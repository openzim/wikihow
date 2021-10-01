# -*- coding: utf-8 -*-

import datetime
import pathlib
import random
import re
import shutil

import bs4
import requests
from jinja2 import Environment, FileSystemLoader
from zimscraperlib.image.convertion import convert_image
from zimscraperlib.image.transformation import resize_image
from zimscraperlib.inputs import handle_user_provided_file
from zimscraperlib.zim.items import URLItem

from .constants import DEFAULT_HOMEPAGE, MAX_HTTP_404_THRESHOLD, ROOT_DIR, Conf
from .shared import Global, GlobalMixin, logger
from .utils import (
    article_ident_for,
    cat_ident_for,
    fix_pagination_links,
    get_categorylisting_url,
    get_digest,
    get_footer_crumbs_from,
    get_footer_links_from,
    get_soup,
    get_soup_of,
    get_subcategories_from,
    normalize_ident,
    parse_css,
    setup_s3_and_check_credentials,
    soup_link_finder,
    to_url,
)


class DomIntegrityError(Exception):
    pass


class wikihow2zim(GlobalMixin):
    def __init__(self, **kwargs):

        Global.conf = Conf(**kwargs)
        for option in Global.conf.required:
            if getattr(Global.conf, option) is None:
                raise ValueError(f"Missing parameter `{option}`")

        # jinja2 environment setup
        self.env = Environment(
            loader=FileSystemLoader(ROOT_DIR.joinpath("templates")), autoescape=True
        )
        self.env.filters["digest"] = get_digest

        # jinja context that we'll pass to all templates
        self.env_context = {"conf": Global.conf}

        # set of all categories we've seen link for
        # used to prevent processing a category twice as they cross-link each other
        self.categories = set()
        # idem, articles can be linked from different categories. we need
        # to keep track of which we processed
        self.articles = set()
        # idem, resources from CSS that we'll downloaded.
        # Source HTML references a dynamic CSS that is built using a varietyof features
        # so it's very common different CSS urls references the same resources (imgs)
        self.resources_digests = set()
        # idem, list of URLs which returned HTTP 404.
        # There are legit scenarios for 404 on wikiHow: login pages
        # we need to track them for later use
        self.missing_articles = set()
        self.missing_categories = set()
        # set of all articles we've seen in related-articles links.
        # we'll go over this at end of categories scrape.
        # those left are not listed in any category
        self.related_articles = set()

    @property
    def build_dir(self):
        return self.conf.build_dir

    def cleanup(self):
        """Remove temp files and release resources before exiting"""
        if not self.conf.keep_build_dir:
            logger.debug(f"Removing {self.build_dir}")
            shutil.rmtree(self.build_dir, ignore_errors=True)

    def get_style_urls(self, soup) -> object:
        """paths list of found CSS link content+resources appended to ZIM"""
        list_css = [
            to_url(lnk.attrs["href"]) for lnk in soup.find_all(soup_link_finder)
        ]
        for url in list_css:
            self.add_css(url)
        return list_css

    def get_online_metadata(self):
        """metadata from online website, looking at homepage source code"""
        logger.debug("Fecthing website metdata")

        soup, _ = get_soup("/")

        # external (<link />) and inline (<style/>) CSS resources
        linked_styles = []
        for link in soup.find_all(soup_link_finder):
            linked_styles.append(to_url(link.attrs["href"]))

        inline_styles = ""
        for style in soup.find_all("style", src=False):
            inline_styles += "\n" + style.string

        return {
            "dir": soup.find("html").attrs["dir"],
            "category_prefix": normalize_ident(
                soup.select("#hp_categories_list a")[0].attrs.get("href")
            ).split(":", 1)[0][1:],
            "homepage_name": normalize_ident(
                soup.select("a#header_logo")[0].attrs.get("href")
            ).replace("/", ""),
            "title": soup.find("title").string,
            "description": soup.find("meta", attrs={"name": "description"}).attrs.get(
                "content"
            ),
            "icon": to_url(soup.find("link", rel="apple-touch-icon").attrs.get("href")),
            "favicon": to_url(soup.find("link", rel="shortcut icon").attrs.get("href")),
            "logo": to_url(soup.select("a#footer_logo img")[0].attrs["src"]),
            "inline_styles": inline_styles,
            "linked_styles": linked_styles,
            "url_special_category": get_categorylisting_url(),
            "footer_links": get_footer_links_from(soup),
        }

    def sanitize_inputs(self):
        """input & metadata sanitation"""
        logger.debug("Checking user-provided metadata")

        if not self.conf.name:
            self.conf.name = "wikihow_{lang}_{selection}".format(
                lang=self.conf.language["iso-639-1"],
                selection="selection" if self.conf.categories else "all",
            )

        period = datetime.datetime.now().strftime("%Y-%m")
        if self.conf.fname:
            # make sure we were given a filename and not a path
            self.conf.fname = pathlib.Path(self.conf.fname.format(period=period))
            if pathlib.Path(self.conf.fname.name) != self.conf.fname:
                raise ValueError(f"filename is not a filename: {self.conf.fname}")
        else:
            self.conf.fname = f"{self.conf.name}_{period}.zim"

        if not self.conf.title:
            self.conf.title = self.metadata["title"]
        self.conf.title = self.conf.title.strip()

        if not self.conf.description:
            self.conf.description = self.metadata["description"]
        self.conf.description = self.conf.description.strip()

        if not self.conf.author:
            self.conf.author = "wikiHow"
        self.conf.author = self.conf.author.strip()

        if not self.conf.publisher:
            self.conf.publisher = "openZIM"
        self.conf.publisher = self.conf.publisher.strip()

        self.conf.tags = list(
            set(
                self.conf.tag
                + ["_category:wikihow", "wikihow", "_videos:yes", "_pictures:yes"]
            )
        )

    def add_illustrations(self):
        logger.debug("Adding illustrations")

        src_illus_fpath = self.build_dir / "illustration"

        # if user provided a custom favicon, retrieve that
        if not self.conf.icon:
            self.conf.icon = self.metadata["icon"]
        handle_user_provided_file(source=self.conf.icon, dest=src_illus_fpath)

        # convert to PNG (might already be PNG but it's OK)
        illus_fpath = src_illus_fpath.with_suffix(".png")
        convert_image(src_illus_fpath, illus_fpath)

        # resize to appropriate size (ZIM uses 48x48 so we double for retina)
        for size in (96, 48):
            resize_image(illus_fpath, width=size, height=size, method="thumbnail")
            with open(illus_fpath, "rb") as fh:
                with self.lock:
                    self.creator.add_illustration(size, fh.read())

        # download and add actual favicon (ICO file)
        favicon_fpath = self.build_dir / "favicon.ico"
        handle_user_provided_file(source=self.metadata["favicon"], dest=favicon_fpath)
        with self.lock:
            self.creator.add_item_for("favicon.ico", fpath=favicon_fpath)

        # download apple-touch-icon
        with self.lock:
            self.creator.add_item(
                URLItem(url=self.metadata["icon"], path="apple-touch-icon.png")
            )

    def get_from_cache(self, url: str) -> bytes:
        """retrieve from local cache if present, otherwise download it first

        Only useful for devel/debug because there are many resources linked
        to assets and source website is quite slow"""
        fpath = self.build_dir.joinpath(f"cache_{get_digest(url)}")
        if fpath.exists():
            with open(fpath, "rb") as fh:
                return fh.read()

        with open(fpath, "wb") as fh:
            content = requests.get(url).content
            fh.write(content)
            return content

    def add_css(self, url: str, inline: bool = False) -> str:
        """Download and add a CSS URL/text, including all its dependencies

        All url() resources from the passed CSS URL/string will be fetched
        and added to ZIM as well. url() will be rewritten in the CSS source
        before adding to Zim"""

        if not inline:
            url = to_url(url)

        # skip if we already added it. Can be referenced from multiple pages
        digest = get_digest(url)
        if digest in self.resources_digests:
            return

        # fetch and transform source CSS
        source = url if inline else self.get_from_cache(url).decode("UTF-8")
        content, resources = parse_css(source)

        # fetch and add to Zim all its resources
        for rsc_url, rsc_path in set(resources):
            rsc_url = to_url(rsc_url)
            rsc_digest = get_digest(rsc_url)

            # skip resource if already handled
            if rsc_digest in self.resources_digests:
                continue

            try:
                with self.lock:
                    # specifically don't specify mimetype here so that scraperlib
                    # determines it from content. We may encounter PNG and SVG
                    self.creator.add_item_for(
                        path=rsc_path,
                        content=self.get_from_cache(rsc_url),
                    )
            except Exception:
                pass  # many are just not working at all
            else:
                self.resources_digests.add(rsc_digest)
                logger.debug(f"> {rsc_path}")

        path = f"assets/{digest}.css"
        with self.lock:
            self.creator.add_item_for(
                path=path,
                content=content,
                mimetype="text/css",
            )
        logger.debug(f"> {path}")
        self.resources_digests.add(digest)
        return digest

    def add_assets(self):
        """download and add site-wide assets, identified in metadata step"""
        logger.info("Adding assets")

        with self.lock:
            self.creator.add_item(
                URLItem(path="assets/logo", url=self.metadata["logo"])
            )
            # external link icons
            for direction in ("ltr", "rtl"):
                url = (
                    f"https://en.wikipedia.org/w/skins/Vector/resources/common/images/"
                    f"external-link-{direction}-icon.svg"
                )
                self.creator.add_item(
                    URLItem(path=f"assets/external-link-{direction}-icon.svg", url=url)
                )

        # handle the external and inline CSS found in homepage
        self.metadata["inline_digest"] = self.add_css(
            self.metadata["inline_styles"], inline=True
        )
        for url in self.metadata["linked_styles"]:
            self.add_css(url)

        # Articles have a custom inline CSS
        soup, _ = get_soup("/wikihow:About-wikiHow")
        self.metadata["article_inline_digest"] = self.add_css(
            "\n".join([style.string for style in soup.find_all("style", src=False)]),
            inline=True,
        )

        # recursively add our own assets, at a path identical to position in repo
        assets_root = pathlib.Path(ROOT_DIR.joinpath("assets"))
        for fpath in assets_root.glob("**/*"):
            if not fpath.is_file():
                continue
            path = str(fpath.relative_to(ROOT_DIR))

            logger.debug(f"> {path}")
            with self.lock:
                self.creator.add_item_for(path=path, fpath=fpath)

    def build_categories_list(self):
        """Parses Sitemap online to get a list of root-level categories"""
        logger.info("Building list of root categories")

        soup, _ = get_soup("/Special:CategoryListing")
        self.conf.categories = [
            cat_ident_for(link.attrs["href"]) for link in soup.select("#catlist a")
        ]

    def build_exclude_lists(self):
        """Using provided path/URL from --excldude, build list of exclusion

        List is stored on rewriter as it is responsible for removing links to
        those articles and categories.
        File must contain Article ID (URL path) or Category: category ID"""
        if not self.conf.exclude:
            return

        logger.info(f"Building exclusion list from {self.conf.exclude}")
        excludes_fpath = self.build_dir / "excludes.lst"
        handle_user_provided_file(source=self.conf.exclude, dest=excludes_fpath)

        with open(excludes_fpath, "r") as fh:
            for line in fh.readlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("Category:"):
                    self.rewriter.excluded_categories.add(line.split("Category:", 1)[1])
                else:
                    self.rewriter.excluded_articles.add(line)

        logger.info(
            f"> {len(self.rewriter.excluded_articles)} articles and "
            f"{len(self.rewriter.excluded_categories)} categories excluded."
        )

    def add_homepage(self):
        logger.info("Building homepage")

        soup, _ = get_soup("/Special:CategoryListing")

        # CategoryListing has custom CSS
        linked_styles = [
            to_url(lnk.attrs["href"]) for lnk in soup.find_all(soup_link_finder)
        ]
        for url in linked_styles:
            self.add_css(url)

        # extract and clean main content
        content = soup.select("div#content_wrapper")[0]
        _ = [script.decompose() for script in content.find_all("script")]

        page = self.env.get_template("home.html").render(
            to_root="./",
            body_classes=" ".join(soup.find("body").attrs.get("class", [])),
            content=self.rewriter.rewrite(content.decode_contents(), to_root="./"),
            page_linked_styles=linked_styles,
            viewport_classes=" ".join(
                soup.find(attrs={"id": "mw-mf-viewport"}).attrs.get("class", [])
            ),
            footer_links=self.metadata["footer_links"],
            title=self.conf.title,
            **self.env_context,
        )

        with self.lock:
            self.creator.add_item_for(
                path=self.metadata["homepage_name"],
                title=self.conf.title,
                content=page,
                mimetype="text/html",
                is_front=True,
            )
            self.creator.add_redirect(
                path=self.metadata["url_special_category"], target_path=DEFAULT_HOMEPAGE
            )

            if DEFAULT_HOMEPAGE != self.metadata["homepage_name"]:
                self.creator.add_redirect(
                    path=DEFAULT_HOMEPAGE, target_path=self.metadata["homepage_name"]
                )

    def scrape_footer_articles(self):
        """Scrape and create all pages found in footer links"""
        for link in self.metadata["footer_links"]:
            # there might be a link to Main-Page which would try (and fail)
            # to create wikiHo Main-Page (already added a redirect in homepage)
            if link.path and link.path != "Main-Page":
                self.scrape_article(link.path, remove_all_links=True)

    def scrape_related_articles(self):
        """Scrape and create all pages found in section related links"""
        for link in list(self.related_articles):
            if self.scrape_article(link) is None:
                self.related_articles.remove(link)

    def scrape_categories(self):
        logger.info("Starting scraping from categories")

        recurse = True  # will fetch sub-categories
        for category in self.conf.categories:
            if category.endswith("/"):
                category = category[:-1]
                recurse = False
            self.scrape_category(category, recurse)

    def scrape_category(self, category: str, recurse: bool = True):
        if category in self.categories or category in self.rewriter.excluded_categories:
            return
        self.categories.add(category)

        logger.info(f"> Category:{category} ({recurse=})")

        nb_pages, sub_categories = self.scrape_category_page(
            category, page_num=1, recurse=recurse
        )

        if nb_pages > 1:
            for page_num in range(2, nb_pages + 1):
                self.scrape_category_page(category, page_num=page_num, recurse=False)

        for sub_category in sub_categories or []:
            self.scrape_category(sub_category)

    def scrape_category_page(self, category: str, page_num: int, recurse: bool):

        category_url = f"/{self.metadata['category_prefix']}:{category}"
        params = {}
        if page_num > 1:
            logger.info(f">> Category:{category} (page={page_num})")
            params = {"pg": page_num}

        try:
            soup, paths = get_soup(category_url, **params)
        except requests.exceptions.HTTPError as exc:
            # don't fail on missing Category (#46)
            if exc.response.status_code == 404:
                logger.warning(">>> HTTP 404, skipping.")
                self.missing_categories.add(category_url)
                return 0, []
            raise exc

        fix_pagination_links(soup)

        articles = set()
        for link in soup.select("#cat_all .responsive_thumb a"):
            articles.add(article_ident_for(link.attrs.get("href")))

        for article in articles:
            if not self.scrape_article(article):
                missing_url = to_url(f"/{article}")
                for a in soup.find_all("a", href=missing_url):
                    del a["href"]
                self.record_missing_url(missing_url)
            # break  # only one article per page

        nb_pages = len(soup.select("#large_pagination ul li"))

        sub_categories = get_subcategories_from(soup, recurse)

        # extract and clean main content
        content = soup.select("div#content_wrapper")[0]

        black_list = (
            "script",
            "noscript > img",
            "noscript:empty",
            "#cat_wca",
            ".cat-promo",
        )
        for selector in black_list:
            _ = [elem.decompose() for elem in content.select(selector)]

        # zim article path
        path = paths.pop()
        if page_num > 1:
            path += f"_pg={page_num}"
        # some categories include a `/`. ex: Système-Macintosh/Apple
        to_root = "./" + ("../" * path.count("/"))

        title = soup.find("title").string
        page = self.env.get_template("category.html").render(
            to_root=to_root,
            body_classes=" ".join(soup.find("body").attrs.get("class", [])),
            content=self.rewriter.rewrite(content.decode_contents(), to_root=to_root),
            page_linked_styles=self.get_style_urls(soup),
            viewport_classes=" ".join(
                soup.find(attrs={"id": "mw-mf-viewport"}).attrs.get("class", [])
                + ["wikihow-category"]
            ),
            footer_links=self.metadata["footer_links"],
            breadcrumbs=get_footer_crumbs_from(soup, self.rewriter.excluded_categories),
            title=title,
            **self.env_context,
        )
        with self.lock:
            self.creator.add_item_for(
                path=path,
                title=title,
                content=page,
                mimetype="text/html",
                is_front=True,
            )

        for redir_path in paths:
            with self.lock:
                self.creator.add_redirect(
                    path=redir_path + (f"_pg={page_num}" if page_num > 1 else ""),
                    target_path=path,
                )

        return nb_pages, sub_categories

    def scrape_article(self, article, remove_all_links=False):
        if article in self.articles or article in self.rewriter.excluded_articles:
            return
        self.articles.add(article)

        logger.info(f">> Article:{article}")

        try:
            soup, _ = get_soup(f"/{article}")
        except requests.exceptions.HTTPError as exc:
            if exc.response.status_code == 404:
                logger.warning(">>> HTTP 404, skipping.")
                return False
            raise exc

        # extract and clean main content
        title = soup.find("title").string
        content = soup.select("div#content_wrapper")[0]

        black_list = (
            "script",
            ".pdf_link",
            "#side_follow",
            "#sidebar_share",
            "#other_languages",
            "#article_rating_mobile",
            "#end_options",
            ".section.tips",
            ".section.bss_share_container",
            ".wh_ad_inner, .wh_ad_active, [data-service=adsense], .wh_ad_spacing",
            "noscript > img",
            "noscript:empty",
            # User success stories
            "#userreviews_mobile",
            # Q&A block
            "#qa >:not(#qa_answered_questions_container)",
            # Expert Q&A
            ".qa_heading sticking",
            "#qa_answered_questions_container #qa_aq_search_container, "
            "#qa_answered_questions_container #qa_add_curated_question",
            ".qa_answer_footer",
            ".qa_no_answered",
            "#qa_see_more_answered",
            "#userreview_recipe_cta",
            "#aboutthisarticle > div.page_stats.section_text",
        )
        for selector in black_list:
            _ = [elem.decompose() for elem in content.select(selector)]

        # Remove link of page of author
        for link in content.select("#coauthor_byline #byline_info > a[href]"):
            del link.attrs["href"]

        if remove_all_links:
            for elem in content.select("a[href]"):
                del elem.attrs["href"]

        for link in content.select("div.section.relatedwikihows a[href]"):
            rel_article = re.sub(r"^/", "", normalize_ident(link.attrs["href"]))
            if rel_article not in self.articles:
                self.related_articles.add(rel_article)

        self.handle_videos_for(soup)

        # some articles include a `/`. ex: Système-Macintosh/Apple
        to_root = "./" + ("../" * article.count("/"))
        page = self.env.get_template("article.html").render(
            to_root=to_root,
            body_classes=" ".join(soup.find("body").attrs.get("class", [])),
            content=self.rewriter.rewrite(content.decode_contents(), to_root=to_root),
            page_linked_styles=self.get_style_urls(soup),
            viewport_classes=" ".join(
                soup.find(attrs={"id": "mw-mf-viewport"}).attrs.get("class", [])
                + ["wikihow-article"]
            ),
            footer_links=self.metadata["footer_links"],
            breadcrumbs=get_footer_crumbs_from(soup, self.rewriter.excluded_categories),
            title=title,
            **self.env_context,
        )
        with self.lock:
            self.creator.add_item_for(
                path=article,
                title=title,
                content=page,
                mimetype="text/html",
                is_front=True,
            )
        return True

    def record_missing_url(self, url):
        self.missing_articles.add(url)

        if len(self.missing_articles) >= MAX_HTTP_404_THRESHOLD:
            logger.debug(
                f"Maximum HTTP 404 threshold reached ({MAX_HTTP_404_THRESHOLD})"
            )

    def handle_videos_for(self, soup: bs4.element.Tag):
        # youtube video blocks
        if self.conf.without_videos:
            # remove link to video block in TOC
            # note that #summaryvideo_toc is different and is not Youtube
            _ = [elem.decompose() for elem in soup.select("#othervideo_toc")]
            # English has a .section.video selector for the video block we target
            # but the class name is localized so it differs from languages.
            # we thus remove the #video parent instead
            _ = [elem.parent.decompose() for elem in soup.select("#video")]
        else:
            for iframe in soup.select(".embedvideocontainer iframe.embedvideo"):
                path = Global.vidgrabber.defer(url=iframe.get("data-src"))
                if path is None:
                    iframe.decompose()
                    continue

                poster = Global.imager.defer(
                    Global.vidgrabber.youtube_poster_url(iframe.get("data-src"))
                )
                iframe.replace_with(
                    get_soup_of(
                        self.env.get_template("video.html").render(
                            path=path,
                            poster=poster,
                            classes=["youtube"],
                            video_format=self.conf.video_format,
                            width=iframe.attrs.get("width", "728"),
                            height=iframe.attrs.get("height", "428"),
                            autoplay="autoplay" in iframe.attrs.get("allow", ""),
                            controls=True,
                            preload=False,
                        ),
                        unwrap=True,
                    )
                )

        # record the video summary section if present.
        # allows distinguishing between step videos and summary one
        try:
            video_summary = soup.select(".summary_with_video")[0]
        except IndexError:
            video_summary = None

        # main-content (step) video hosted by wikiHow
        for video in soup.select(".video-player .video-container video"):
            # skip our own videos
            if "wikihow2zim" in video.attrs.get("class"):
                continue

            url = video.attrs.get("src")
            if not url and not video.attrs.get("data-src"):
                # missing source
                video.decompose()
                continue
            if not url:
                url = to_url(f"/video{video.attrs.get('data-src')}")

            path = Global.vidgrabber.defer(url=to_url(url))
            if path is None:
                continue

            poster_path = Global.imager.defer(
                url=to_url(video.attrs.get("poster", video.attrs.get("data-poster")))
            )
            # remove extra “controls” and watermark (from .video-player) :requires JS
            for elem in video.parent.parent.select(".m-video-controls, .m-video-wm"):
                elem.decompose()

            show_controls = video_summary and video in video_summary.select("video")
            video.replace_with(
                get_soup_of(
                    self.env.get_template("video.html").render(
                        path=path,
                        poster=poster_path,
                        classes=" ".join(video.attrs.get("class")),
                        video_format=self.conf.video_format,
                        autoplay=True,
                        muted="muted" in video.attrs,
                        loop="loop" in video.attrs,
                        playsinline="playsinline" in video.attrs,
                        controls=show_controls,
                        preload=True,
                    )
                )
            )

        # related articles links using video as thumbnail
        for video in soup.select("#relatedwikihows .related-wh video"):
            if "wikihow2zim" in video.attrs.get("class"):
                continue

            url = video.attrs.get("src")
            if not url and not video.attrs.get("data-src"):
                # missing source
                video.decompose()
                continue

            if not url:
                url = to_url(f"/video{video.attrs.get('data-src')}")

            poster_path = Global.imager.defer(
                url=to_url(video.attrs.get("poster", video.attrs.get("data-poster")))
            )
            path = Global.vidgrabber.defer(url=to_url(url))
            if path is None:
                video.decompose()
                continue

            video.replace_with(
                get_soup_of(
                    self.env.get_template("video.html").render(
                        path=path,
                        poster=poster_path,
                        classes=" ".join(video.attrs.get("class")),
                        video_format=self.conf.video_format,
                        autoplay=True,
                        width=video.attrs.get("width", "342"),
                        height=video.attrs.get("height", "184"),
                        alt=video.attrs.get("alt"),
                        muted="muted" in video.attrs,
                        loop="loop" in video.attrs,
                        playsinline="playsinline" in video.attrs,
                        controls=False,
                        preload=True,
                    )
                )
            )

    def check_dom_integrity(self):
        """Checking wikiHow DOM Integrity

        Verifying that the elements we rely on for the scrape are in place
        so we can fail early if not: meaning source changed significantly"""

        logger.info("Ensuring source site DOM Integrity")

        logger.debug("> checking CategoryListing")

        soup, _ = get_soup("/Special:CategoryListing")
        if not soup.select("#content_wrapper"):
            raise DomIntegrityError("#content_wrapper not found")
        category_links = soup.select("#catlist_container #catlist a")

        if not category_links:
            raise DomIntegrityError("No links in #catlist_container")

        # selecting a randon element in the list of links.
        # these links should all be Category links
        # we'll reuse selected link to check Category page later
        category_link = category_links[
            random.randint(0, len(category_links) - 1)
        ].attrs.get("href")
        if not category_link:
            raise DomIntegrityError("Category link has no href")

        # Making sure it was an actual Category link
        category_id = cat_ident_for(category_link)
        if not re.findall(":", category_link):
            raise DomIntegrityError("has not category link")

        category_req_url = normalize_ident(to_url(f"/Category:{category_id}"))
        resp = requests.get(category_req_url)
        if resp.status_code != 200:
            raise DomIntegrityError(f"Category link if not valid ({resp})")

        logger.debug("> checking Category Page")

        # Category page is mostly a grid listing articles in the Category
        soup, _ = get_soup(f"/Category:{category_id}")
        if not soup.select("#cat_all > div.cat_grid"):
            raise DomIntegrityError("Article list not found in #cat_grid")

        logger.debug("> checking Article Page")

        # Using Randomizer to select a random article from source website
        soup, _ = get_soup("/Special:Randomizer")

        # Checking that we have a title where expected
        if not soup.select("#content_inner > div.pre-content h1"):
            raise DomIntegrityError("Article title not found (h1)")

    def run(self):
        s3_storage = (
            setup_s3_and_check_credentials(self.conf.s3_url_with_credentials)
            if self.conf.s3_url_with_credentials
            else None
        )
        s3_msg = (
            f"\n"
            f"  using cache: {s3_storage.url.netloc} "
            f"with bucket: {s3_storage.bucket_name}"
            if s3_storage
            else ""
        )
        del s3_storage

        logger.info(
            f"Starting scraper with:\n"
            f"  language: {self.conf.language['english']}"
            f" ({self.conf.domain})\n"
            f"  output_dir: {self.conf.output_dir}\n"
            f"  build_dir: {self.build_dir}\n"
            f"  categories: "
            f"{', '.join(self.conf.categories)if self.conf.categories else 'all'}"
            f"{s3_msg}"
        )

        if not self.conf.skip_dom_check:
            self.check_dom_integrity()

        Global.metadata = self.get_online_metadata()
        logger.debug(
            f"homepage_name: {self.metadata['homepage_name']}\n"
            f"category_prefix: {self.metadata['category_prefix']}\n"
            f"url_special_category: {self.metadata['url_special_category']}\n"
            f"dir: {self.metadata['dir']}\n"
            f"title: {self.metadata['title']}\n"
            f"description: {self.metadata['description']}\n"
            f"icon: {self.metadata['icon']}\n"
            f"favicon: {self.metadata['favicon']}\n"
            f"logo: {self.metadata['logo']}"
        )
        self.sanitize_inputs()

        logger.debug("Starting Zim creation")
        Global.setup()
        self.creator.start()

        try:
            self.add_illustrations()
            self.add_assets()
            self.env_context.update(
                {
                    "dir": self.metadata["dir"],
                    "lang": self.conf.lang_code,
                    "linked_styles": self.metadata["linked_styles"],
                    "inline_digest": self.metadata["inline_digest"],
                    "homepage_name": self.metadata["homepage_name"],
                }
            )

            self.build_exclude_lists()

            if not self.conf.categories:
                self.build_categories_list()

            # start adding ZIM pages
            self.add_homepage()

            if not self.conf.skip_footer_links:
                self.scrape_footer_articles()

            if self.conf.single_article:
                self.scrape_article(self.conf.single_article)
            else:
                self.scrape_categories()

            if not self.conf.skip_relateds:
                self.scrape_related_articles()

            logger.info(
                f"Stats: {len(self.categories)} categories, "
                f"{len(self.articles)} articles, "
                f"{len(self.missing_categories)} missing categories, "
                f"{len(self.missing_articles)} missing articles, "
                f"{len(self.related_articles)} related articles, "
                f"{self.imager.nb_requested} images, "
                f"{self.vidgrabber.nb_requested} videos"
            )

            logger.info("Awaiting images")
            Global.img_executor.shutdown()

            logger.info("Awaiting videos")
            Global.video_executor.shutdown()

        except Exception as exc:
            # request Creator not to create a ZIM file on finish
            self.creator.can_finish = False
            if isinstance(exc, KeyboardInterrupt):
                logger.error("KeyboardInterrupt, exiting.")
            else:
                logger.error(f"Interrupting process due to error: {exc}")
                logger.exception(exc)
            self.imager.abort()
            Global.img_executor.shutdown(wait=False)
            return 1
        else:
            logger.info("Finishing ZIM file")
            # we need to release libzim's resources.
            # currently does nothing but crash if can_finish=False but that's awaiting
            # impl. at libkiwix level
            with self.lock:
                self.creator.finish()
            logger.info(
                f"Finished Zim {self.creator.filename.name} "
                f"in {self.creator.filename.parent}"
            )
        finally:
            self.cleanup()
