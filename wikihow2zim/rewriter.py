# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import collections
import re
import urllib.parse

import bs4

from .shared import GlobalMixin, logger
from .utils import normalize_ident, rebuild_uri

seldef = collections.namedtuple(
    "SelectorDef",
    [
        "selector",
        "for_category",
        "target_is_parent",
        "clear_parent_previous_sibling",
    ],
)


def remove_link_for_exclusion(link, selector_def):
    """remove a link or its parent based on selector_def"""
    if selector_def.clear_parent_previous_sibling:
        link.parent.previous_sibling.replace_with("")

    if selector_def.target_is_parent:
        link.parent.decompose()
    else:
        link.decompose()


def is_in_code(elem):
    """whether this node is inside a <code /> one

    <code/> blocks are used to share code and are thus usually not rewritten"""
    for parent in elem.parents:
        if parent.name in ("code", "pre"):
            return True
    return False


def is_child_of(elem, selector, soup):
    """whether element is a child of element mathcing selector"""
    target = soup.select(selector)
    return target and target[0] in elem.parents


def has_parent_tagged(elem, name):
    """whether element has a parent which such tag name"""
    for parent in elem.parents:
        if parent.name == name:
            return parent


class Rewriter(GlobalMixin):
    def __init__(self):
        self.domain_re = re.compile(rf"https?://{self.conf.domain}(?P<path>/.+)")

        # sets of articles and categories that should not be included
        # filled by --exclude option
        self.excluded_articles = set()
        self.excluded_categories = set()

    def rewrite(self, content: str, to_root: str = "", unwrap: bool = False):
        if not content:
            return ""

        try:
            soup = bs4.BeautifulSoup(content, "lxml")
        except Exception as exc:
            logger.error(f"Unable to init soup for {content}: {exc}")
            return content
        if not soup:
            return ""

        for attr in ("body", "html"):
            getattr(soup, attr).unwrap()

        self.rewrite_links(soup, to_root)
        self.rewrite_links_for_excludes(soup, to_root)

        self.rewrite_pictures(soup, to_root)

        self.rewrite_images(soup, to_root)

        return str(soup)

    def rewrite_links(self, soup, to_root):
        # rewrite links targets
        for link in soup.find_all("a", href=True):

            # don't bother empty href=""
            if not link.get("href", "").strip():
                # remove link to ""
                del link["href"]
                continue

            # Ignore reference links on the page
            if link["href"].startswith("#"):
                continue

            # skip links inside <code /> nodes
            if is_in_code(link):
                continue

            link["href"] = link["href"].strip()

            is_relative = link["href"][0] in ("/", ".") or not link["href"].startswith(
                "http"
            )

            if not is_relative:
                match = self.domain_re.match(link["href"])
                if match:
                    is_relative = True
                    # make the link relative and remove / so it's Zim compat
                    link["href"] = match.groupdict().get("path")[1:]

            # rewrite relative links to match our in-zim URIs
            if is_relative:
                # might be a relative link for which we don't offer an offline
                # version. ex: /help/*
                if not self.rewrite_relative_link(link, to_root):
                    continue

            # link is not relative, apply rules
            self.rewrite_external_link(link)

    def rewrite_external_link(self, link):
        link["class"] = " ".join(link.get("class", []) + ["external-link"])
        if self.conf.without_external_links:
            del link["href"]

    def rewrite_relative_link(self, link: bs4.element.Tag, to_root: str) -> bool:
        """whether to consider link as non-relative because we failed to rewrite"""

        # link to root (/)
        if link["href"] == "":
            link["href"] = to_root
            return

        try:
            uri = urllib.parse.urlparse(link["href"])
            # normalize path as if from root.
            # any folder-walking link is considered to be targetting root
            uri_path = re.sub(r"^(\.\.?/)+", "", uri.path)
            uri_path = re.sub(r"^/", "", uri_path)
        except Exception as exc:
            logger.error(f"Failed to parse link target {link['href']}: {exc}")
            # consider this external
            return True

        # Normalize with to_root
        link["href"] = rebuild_uri(
            uri=uri,
            path=f"{to_root}{uri_path}",
            failsafe=True,
        ).geturl()

    def rewrite_links_for_excludes(self, soup, to_root):
        if not self.conf.exclude:
            return

        article_re = re.compile(r"^" + to_root + r"(?P<path>.+)")
        category_re = re.compile(
            r"^" + to_root + self.metadata["category_prefix"] + r":(?P<path>.+)"
        )

        selectors = [
            # related articles in article page
            seldef("#relatedwikihows > a.related-wh[href]", False, False, False),
            # link to article in category page
            seldef("#cat_all div.responsive_thumb > a[href]", False, True, False),
            # sub category link in category page
            seldef("#subcats > ul a[href]", True, True, False),
            # categorlyListing thumbnail link (english)
            seldef(".cat_container a[href]", True, True, False),
            # categorylisting link to category
            seldef("#catlist_container #catlist a[href]", True, True, False),
            # top breadcrumb in article page
            seldef(".breadcrumbs a[href]", True, True, False),
            # list of categories article is in  - in About section of article page
            seldef(".sp_box.sp_fullbox a[href]", True, True, True),
        ]

        for sdef in selectors:
            for link in soup.select(sdef.selector):
                href = normalize_ident(link.attrs["href"])
                if sdef.for_category:
                    match = category_re.match(href)
                    if (
                        match
                        and match.groupdict().get("path") in self.excluded_categories
                    ):
                        remove_link_for_exclusion(link, sdef)
                else:
                    match = article_re.match(href)
                    if (
                        match
                        and match.groupdict().get("path") in self.excluded_articles
                    ):
                        remove_link_for_exclusion(link, sdef)

    def rewrite_images(self, soup, to_root):
        for img in soup.find_all("img"):
            if img.attrs.get("onload"):
                del img.attrs["onload"]

            if not img.get("src") and not img.get("data-src"):
                continue

            if img.get("data-src") and not img.get("src"):
                img["src"] = img["data-src"]
                del img["data-src"]
                try:
                    del img["data-src-nowebp"]
                except KeyError:
                    pass

            # skip links inside <code /> nodes
            if is_in_code(img):
                continue

            # will introduce Webp Polyfill later
            # img["onerror"] = "onImageLoadingError(this);"
            path = self.imager.defer(img["src"])
            if path is None:
                del img["src"]
            else:
                img["src"] = f"{to_root}{path}"

    def rewrite_pictures(self, soup, to_root):
        """remove all elements (source mostly) inside picture except img

        pictures are used where there are webp version and the img is used as
        fallback."""
        for picture in soup.find_all("picture"):
            # there's no fallback img, we can't remove sources
            if not picture.find("img"):
                continue

            for child in picture.contents:
                if isinstance(child, bs4.element.Tag) and child.name != "img":
                    child.decompose()
