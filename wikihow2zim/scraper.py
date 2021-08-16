# -*- coding: utf-8 -*-

import pathlib
import requests

import bs4
from jinja2 import Environment, FileSystemLoader
from zimscraperlib.zim.creator import Creator
from zimscraperlib.zim.items import URLItem

from .constants import URLS, getLogger, ROOT_DIR

logger = getLogger()
options = [
    "language",
    "name",
    "publisher",
    "tags",
    "output_dir",
    "tmp_dir",
    "fname",
    "keep_build_dir",
    "low_quality",
    "no_external_links",
    "s3_url_with_credentials",
    "debug",
]


class wikihow2zim:
    def __init__(self, **kwargs):

        for option in options:
            if option not in kwargs:
                raise ValueError(f"Missing parameter `{option}`")

        for option in options:
            setattr(self, option, kwargs[option])

        # Create output directory
        pathlib.Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        # get URL for selected language
        self.url = URLS[self.language]

        # jinja2 environment setup
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir), autoescape=True
        )

    @property
    def templates_dir(self):
        return ROOT_DIR.joinpath("templates")

    def add_icon(self):
        try:
            response = requests.get(self.url)
        except Exception as exc:
            logger.critical(f"Unable to retrieve homepage at {self.url}: {exc}")
            logger.exception(exc)
            return 1

        soup = bs4.BeautifulSoup(response.content, "lxml")

        icon = soup.find(name="link", attrs={"rel": "apple-touch-icon"})
        if icon:
            icon_resp = requests.get(icon.attrs.get("href"))
            self.creator.add_illustration(48, icon_resp.content)

    def add_assets(self):
        assets_root = pathlib.Path(ROOT_DIR.joinpath("assets"))
        for fpath in assets_root.glob("**/*"):
            if not fpath.is_file():
                continue
            self.creator.add_item_for(
                path=str(fpath.relative_to(ROOT_DIR)), fpath=fpath
            )

    def get_article(self, article_url):
        try:
            response = requests.get(article_url)
        except Exception as exc:
            logger.critical(f"Unable to retrieve homepage at {cat_url}: {exc}")
            logger.exception(exc)

        soup = bs4.BeautifulSoup(response.text, "html.parser")

        # Get the article title
        article_title = soup.find("div", {"class": "pre-content"}).find("h1").text

        # Get the intro
        intro = (
            soup.find("div", {"id": "intro"}).find("div", {"id": "mf-section-0"}).text
        )

        # Get the methods/parts
        methods = []

        for node in soup.find_all("div", {"class": "steps"}):

            method = {}

            # Get method title
            method["title"] = node.find("span", {"class": "mw-headline"}).text

            # Get method sections:
            method["steps"] = []
            steps_list = node.find("div", {"class": "section_text"}).select(
                "li[id*=step-id]"
            )

            # Get the title, text and images for all the steps in the given method/part
            for s in steps_list:

                step = {}
                image = s.find("a", {"class": "image"})
                if image is not None:
                    step["image"] = image["href"]
                else:
                    step["image"] = None

                step["title"] = str(
                    s.find("div", {"class": "step"}).find("b", {"class": "whb"}).text
                )

                text = s.find("div", {"class": "step"})
                if text.find("script"):
                    text.find("script").decompose()
                if text.find("b", {"class": "whb"}):
                    text.find("b", {"class": "whb"}).decompose()
                sups = text.find_all("sup")
                for ss in sups:
                    ss.decompose()
                step["text"] = text

                method["steps"].append(step)

            methods.append(method)

        sys.exit()

        article = self.env.get_template("article.html")
        self.creator.add_item_for(
            path="category/" + article_title,
            title="article_title",
            content=article.render(title=article_title, intro=intro, methods=methods),
            mimetype="text/html",
        )

    def walk_subcategories(self, main_wiki_url, cat_url, recursion_depth):
        try:
            response = requests.get(cat_url)
        except Exception as exc:
            logger.critical(f"Unable to retrieve homepage at {cat_url}: {exc}")
            logger.exception(exc)

        soup = bs4.BeautifulSoup(response.text, "html.parser")
        article_divs = soup.find_all("div", {"class": "responsive_thumb"})
        for article_div in article_divs:
            article_url = article_div.find("a")["href"]
            if not article_url in self.articles_list:
                self.articles_list[article_url] = [str(recursion_depth) + " " + cat_url]
                self.get_article(article_url)
            else:
                self.articles_list[article_url].append(
                    str(recursion_depth) + " " + cat_url
                )

        subcat_divs = soup.find_all("div", {"class": "subcat_container"})
        for subcat_div in subcat_divs:
            subcat_url = main_wiki_url + subcat_div.find("a")["href"]
            if not subcat_url in self.subcat_list:
                self.subcat_list[subcat_url] = [str(recursion_depth) + " " + cat_url]
            else:
                self.subcat_list[subcat_url].append(
                    str(recursion_depth) + " " + cat_url
                )
            print(str(recursion_depth) + " category " + subcat_url, flush=True)
            self.walk_subcategories(main_wiki_url, subcat_url, recursion_depth + 1)

    def walk_categories(self):
        # Get all the articles by walking through all the main categories
        # and the sub-categories

        self.articles_list = {}  # keep track of each article processed and
        # where each article was referenced from
        self.subcat_list = {}  # keep track of each subcategory processed, and
        # where each subcategory was referenced from

        main_wiki_url = "https://www.wikihow.com"
        sitemap_url = "https://www.wikihow.com/Special:Sitemap"

        try:
            response = requests.get(sitemap_url)
        except Exception as exc:
            logger.critical(f"Unable to retrieve homepage at {url}: {exc}")
            logger.exception(exc)

        soup = bs4.BeautifulSoup(response.text, "html.parser")

        # Find main categories
        category_divs = soup.find_all("div", {"class": "cat_list"})
        self.main_categories = []
        for div in category_divs:
            h3 = div.find("h3")
            cat_url = main_wiki_url + h3.find("a")["href"]
            print("0 category " + cat_url, flush=True)
            current_category = [h3.text, self.output_dir + "/C" + h3.find("a")["href"]]
            self.main_categories.append(current_category)
            self.walk_subcategories(main_wiki_url, cat_url, 1)

    def add_homepage(self):
        # Add content to zim file
        template = self.env.get_template("home.html")
        self.creator.add_item_for(
            path="Home",
            title="Home",
            content=template.render(
                title="Home", description="Home", main_categories=self.main_categories
            ),
            mimetype="text/html",
        )

        # Add wikihow logo:
        url = (
            "https://www.wikihow.com/extensions/wikihow/mobile"
            "/images/wikihow_logo_230.png"
        )
        self.creator.add_item(
            URLItem(
                url=url,
                path="assets/static/wikihow_logo.png",
                mimetype="image/png",
            )
        )

    def run(self):
        logger.info("Running the scraper")

        # Set up the output zim file:
        fpath = pathlib.Path(self.output_dir).joinpath("output.zim")
        self.creator = Creator(filename=fpath).set_mainpath("Home")
        self.creator.start()

        self.add_icon()

        self.add_assets()

        self.walk_categories()

        self.add_homepage()

        logger.debug(self.articles_list)
        logger.debug(self.subcat_list)

        self.creator.finish()
