# -*- coding: utf-8 -*-

from jinja2 import Environment, FileSystemLoader

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

        self.url = URLS[self.language]

        # jinja2 environment setup
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)), autoescape=True
        )

    @property
    def templates_dir(self):
        return ROOT_DIR.joinpath("templates")

    def run(self):
        logger.info(
            f"running the scraper with the following arguments: \n{self.__dict__}"
        )

        template = self.env.get_template("base.html")

        logger.info(template.render(title="base", description="d"))
