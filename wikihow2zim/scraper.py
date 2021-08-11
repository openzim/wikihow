# -*- coding: utf-8 -*-

import os
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
        url = "https://www.wikihow.com/extensions/wikihow/mobile/images/wikihow_logo_230.png"
        self.creator.add_item(
            URLItem(
                url=url,
                path="assets/static/wikihow_logo.png",
                mimetype="image/png",
            )
        )

    def run(self):
        logger.info(f"Running the scraper")

        # Set up the output zim file:
        fpath = pathlib.Path(self.output_dir).joinpath("output.zim")
        self.creator = Creator(filename=fpath).set_mainpath("Home")
        self.creator.start()

        # fetch icon from website and set it as Zim Icon
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

        self.add_assets()

        self.add_homepage()

        self.creator.finish()
