# -*- coding: utf-8 -*-

import shutil
import pathlib
import requests
import datetime

import bs4
from jinja2 import Environment, FileSystemLoader

from zimscraperlib.zim.creator import Creator
from zimscraperlib.zim.items import URLItem
from zimscraperlib.inputs import handle_user_provided_file
from zimscraperlib.image.convertion import convert_image
from zimscraperlib.image.transformation import resize_image

from .constants import Conf, getLogger, ROOT_DIR

logger = getLogger()


class wikihow2zim:
    def __init__(self, **kwargs):

        self.conf = Conf(**kwargs)
        for option in self.conf.required:
            if getattr(self.conf, option) is None:
                raise ValueError(f"Missing parameter `{option}`")

        # jinja2 environment setup
        self.env = Environment(
            loader=FileSystemLoader(ROOT_DIR.joinpath("templates")), autoescape=True
        )

    @property
    def build_dir(self):
        return self.conf.build_dir

    def cleanup(self):
        """Remove temp files and release resources before exiting"""
        if not self.conf.keep_build_dir:
            logger.debug(f"Removing {self.build_dir}")
            shutil.rmtree(self.build_dir, ignore_errors=True)

    def get_url(self, path: str) -> str:
        return f"{self.conf.main_url.geturl()}{path}"

    def fetch(self, path: str) -> str:
        resp = requests.get(url=self.get_url(path))
        resp.raise_for_status()
        return resp.text

    def get_online_metadata(self):
        soup = bs4.BeautifulSoup(self.fetch("/"), "lxml")

        def to_url(value):
            return value if value.startswith("http") else self.get_url(value)

        return {
            "title": soup.find("title").text,
            "description": soup.find("meta", attrs={"name": "description"}).attrs.get(
                "content"
            ),
            "icon": to_url(soup.find("link", rel="apple-touch-icon").attrs.get("href")),
            "favicon": to_url(soup.find("link", rel="shortcut icon").attrs.get("href")),
        }

    def sanitize_inputs(self):
        """input & metadata sanitation"""

        if not self.conf.name:
            self.conf.name = "wikihow_{lang}_{selection}".format(
                lang=self.conf.language["iso-639-3"],
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
            self.conf.publisher = "Openzim"
        self.conf.publisher = self.conf.publisher.strip()

        self.conf.tags = list(set(self.conf.tag + ["_category:other", "wikihow"]))

    def add_illustrations(self):
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
                self.creator.add_illustration(size, fh.read())

        # download and add actual favicon (ICO file)
        favicon_fpath = self.build_dir / "favicon.ico"
        handle_user_provided_file(source=self.metadata["favicon"], dest=favicon_fpath)
        self.creator.add_item_for("favicon.ico", fpath=favicon_fpath)

        # download apple-touch-icon
        self.creator.add_item(
            URLItem(url=self.metadata["icon"], path="apple-touch-icon.png")
        )

    def add_assets(self):

        assets_root = pathlib.Path(ROOT_DIR.joinpath("assets"))
        for fpath in assets_root.glob("**/*"):
            if not fpath.is_file():
                continue
            self.creator.add_item_for(
                path=str(fpath.relative_to(ROOT_DIR)), fpath=fpath
            )

    def run(self):
        logger.info(
            f"Starting scraper with:\n"
            f"  language: {self.conf.language['english']}"
            f" ({self.conf.main_url.netloc})\n"
            f"  output_dir: {self.conf.output_dir}\n"
            f"  build_dir: {self.build_dir}\n"
            f"  categories: "
            f"{', '.join(self.conf.categories)if self.conf.categories else 'all'}"
        )

        logger.debug("fetching online metadata")
        self.metadata = self.get_online_metadata()

        self.sanitize_inputs()

        self.creator = Creator(
            filename=self.conf.output_dir.joinpath(self.conf.fname),
            main_path="home",
            favicon_path="illustration",
            language=self.conf.language["iso-639-3"],
            title=self.conf.title,
            description=self.conf.description,
            creator=self.conf.author,
            publisher=self.conf.publisher,
            name=self.conf.name,
            tags=";".join(self.conf.tags),
            date=datetime.date.today(),
        ).config_verbose(True)

        self.creator.start()

        self.add_illustrations()
        self.add_assets()

        self.creator.finish()

        self.cleanup()
