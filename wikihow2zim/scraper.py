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

    def add_homepage(self):
        template = self.env.get_template("base.html")
        self.creator.add_item_for(
            path="Home",
            title="Home",
            content=template.render(title="Home", description="Home"),
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

    def walk_subcategories(self, main_wiki_url, cat_url, recursion_depth):
        try:
            response = requests.get(cat_url)
        except Exception as exc:
            logger.critical(f"Unable to retrieve homepage at {curl}: {exc}")
            logger.exception(exc)

        soup = bs4.BeautifulSoup(response.text, "html.parser")
        article_divs = soup.find_all("div", {"class": "responsive_thumb"})
        for article_div in article_divs:
            article_url = article_div.find("a")["href"]
            if not article_url in self.articles_list:
                self.articles_list[article_url] = [str(recursion_depth) + " " + cat_url]
                # get html create zim
            else:
                self.articles_list[article_url].append(str(recursion_depth) + " " + cat_url)

        subcat_divs = soup.find_all("div", {"class": "subcat_container"})
        for subcat_div in subcat_divs:
            subcat_url = main_wiki_url + subcat_div.find("a")["href"]
            if not subcat_url in self.subcat_list:
                self.subcat_list[subcat_url] = [str(recursion_depth) + " " + cat_url]
            else:
                self.subcat_list[subcat_url].append(str(recursion_depth) + " " + cat_url)
            print(str(recursion_depth) + " category " + subcat_url, flush=True)
            self.walk_subcategories(main_wiki_url, subcat_url, recursion_depth + 1)


    def walk_categories(self):
        # Get all the articles by walking through all the main categories
        # and the sub-categories

        self.articles_list = {} # keep track of each article processed and
                                # where each article was referenced from
        self.subcat_list = {} # keep track of each subcategory processed, and
                                # where each subcategory was referenced from

        main_wiki_url = "https://www.wikihow.com"
        sitemap_url = "https://www.wikihow.com/Special:Sitemap"

        try:
            response = requests.get(sitemap_url)
        except Exception as exc:
            logger.critical(f"Unable to retrieve homepage at {url}: {exc}")
            logger.exception(exc)

        soup = bs4.BeautifulSoup(response.text, "html.parser")

        category_divs = soup.find_all("div", {"class": "cat_list"})
        counts = 0
        for div in category_divs:
            # Main Categories
            h3 = div.find_all("h3")
            for h in h3:
                cat_url = main_wiki_url + h.find("a")["href"]
                print("0 category " + cat_url, flush=True)
                self.walk_subcategories(main_wiki_url, cat_url, 1)
                counts = counts + 1
            if counts >= 1:
                break


    def run(self):
        logger.info("Running the scraper")

        # Set up the output zim file:
        fpath = pathlib.Path(self.output_dir).joinpath("output.zim")
        self.creator = Creator(filename=fpath).set_mainpath("Home")
        self.creator.start()

        self.add_icon()

        self.add_assets()

        self.add_homepage()

        self.walk_categories()

        print(self.articles_list)
        print(self.subcat_list)

        self.creator.finish()
