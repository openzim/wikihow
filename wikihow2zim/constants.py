# -*- coding: utf-8 -*-

import pathlib
import logging

from zimscraperlib.logging import getLogger as lib_getLogger

ROOT_DIR = pathlib.Path(__file__).parent
NAME = ROOT_DIR.name

with open(ROOT_DIR.joinpath("VERSION"), "r") as fh:
    VERSION = fh.read().strip()

SCRAPER = f"{NAME} {VERSION}"

URLS = {
    "en": "https://www.wikihow.com",
    "es": "https://es.wikihow.com",
    "pt": "https://pt.wikihow.com",
    "it": "https://www.wikihow.it",
    "fr": "https://fr.wikihow.com",
    "ru": "https://ru.wikihow.com",
    "de": "https://de.wikihow.com",
    "zh": "https://zh.wikihow.com",
    "nl": "https://nl.wikihow.com",
    "cz": "https://www.wikihow.cz",
    "id": "https://id.wikihow.com",
    "jp": "https://www.wikihow.jp",
    "hi": "https://hi.wikihow.com",
    "th": "https://th.wikihow.com",
    "ar": "https://ar.wikihow.com",
    "vn": "https://www.wikihow.vn",
    "ko": "https://ko.wikihow.com",
    "tr": "https://www.wikihow.com.tr"
}


class Global:
    debug = False


def setDebug(debug):
    """toggle constants global DEBUG flag (used by getLogger)"""
    Global.debug = bool(debug)


def getLogger():
    """configured logger respecting DEBUG flag"""
    return lib_getLogger(NAME, level=logging.DEBUG if Global.debug else logging.INFO)
