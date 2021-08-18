# -*- coding: utf-8 -*-

import pathlib
import logging
import tempfile
import urllib.parse
from typing import Optional, List
from dataclasses import dataclass, field

from zimscraperlib.logging import getLogger as lib_getLogger
from zimscraperlib.i18n import get_language_details

ROOT_DIR = pathlib.Path(__file__).parent
NAME = ROOT_DIR.name

with open(ROOT_DIR.joinpath("VERSION"), "r") as fh:
    VERSION = fh.read().strip()

SCRAPER = f"{NAME} {VERSION}"


class Global:
    debug = False


def setDebug(debug):
    """toggle constants global DEBUG flag (used by getLogger)"""
    Global.debug = bool(debug)


def getLogger():
    """configured logger respecting DEBUG flag"""
    return lib_getLogger(NAME, level=logging.DEBUG if Global.debug else logging.INFO)


URLS = {
    "en": "https://www.wikihow.com",
    "ar": "https://ar.wikihow.com",
    "cs": "https://www.wikihow.cz",
    "de": "https://de.wikihow.com",
    "es": "https://es.wikihow.com",
    "fa": "https://wikihowfarsi.com",
    "fr": "https://fr.wikihow.com",
    "hi": "https://hi.wikihow.com",
    "id": "https://id.wikihow.com",
    "it": "https://www.wikihow.it",
    "ja": "https://www.wikihow.jp",
    "ko": "https://ko.wikihow.com",
    "nl": "https://nl.wikihow.com",
    "pt": "https://pt.wikihow.com",
    "ru": "https://ru.wikihow.com",
    "th": "https://th.wikihow.com",
    "tr": "https://www.wikihow.com.tr",
    "vi": "https://www.wikihow.vn",
    "zh": "https://zh.wikihow.com",
}


@dataclass
class Conf:
    required = [
        "lang_code",
        "output_dir",
    ]

    lang_code: str

    # zim params
    name: str
    title: Optional[str] = ""
    description: Optional[str] = ""
    author: Optional[str] = ""
    publisher: Optional[str] = ""
    fname: Optional[str] = ""
    tag: List[str] = field(default_factory=list)

    # customization
    icon: Optional[str] = ""

    # filesystem
    _output_dir: Optional[str] = "."
    _tmp_dir: Optional[str] = "."
    output_dir: Optional[pathlib.Path] = None
    tmp_dir: Optional[pathlib.Path] = None

    # performances
    nb_threads: Optional[int] = -1
    s3_url_with_credentials: Optional[str] = ""

    # quality
    without_images: Optional[bool] = False
    without_external_links: Optional[bool] = False
    low_quality: Optional[bool] = False

    # debug/devel
    categories: List[str] = field(default_factory=list)
    build_dir_is_tmp_dir: Optional[bool] = False
    keep_build_dir: Optional[bool] = False
    debug: Optional[bool] = False
    stats_filename: Optional[str] = None

    @staticmethod
    def get_url(lang_code):
        return urllib.parse.urlparse(URLS[lang_code])

    @property
    def s3_url(self):
        return self.s3_url_with_credentials

    def __post_init__(self):
        self.main_url = Conf.get_url(self.lang_code)
        self.language = get_language_details(self.lang_code)
        self.output_dir = pathlib.Path(self._output_dir).expanduser().resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if self.tmp_dir:
            self.tmp_dir.mkdir(parents=True, exist_ok=True)
        if self.build_dir_is_tmp_dir:
            self.build_dir = self.tmp_dir
        else:
            self.build_dir = pathlib.Path(
                tempfile.mkdtemp(prefix=f"{self.main_url.netloc}_", dir=self.tmp_dir)
            )

        if self.stats_filename:
            self.stats_filename = pathlib.Path(self.stats_filename).expanduser()
            self.stats_filename.parent.mkdir(parents=True, exist_ok=True)
