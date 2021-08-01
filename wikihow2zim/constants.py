# -*- coding: utf-8 -*-

import pathlib

from zimscraperlib.logging import getLogger as lib_getLogger

ROOT_DIR = pathlib.Path(__file__).parent
NAME = ROOT_DIR.name

def getLogger():
    """ configured logger respecting DEBUG flag """
    return lib_getLogger(NAME, level=logging.DEBUG if Global.debug else logging.INFO)

