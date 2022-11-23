#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu
# pylint: disable=cyclic-import

import datetime
import logging
import threading
import time

from zimscraperlib.download import get_session
from zimscraperlib.logging import getLogger as lib_getLogger
from zimscraperlib.zim.creator import Creator

from .constants import DEFAULT_HOMEPAGE, NAME


class Global:
    """Shared context accross all scraper components"""

    debug = False
    logger = lib_getLogger(
        NAME,
        level=logging.INFO,
        log_format="[%(threadName)s::%(asctime)s] %(levelname)s:%(message)s",
    )
    conf = None

    session = get_session(max_retries=10)

    metadata = {}

    creator = None
    imager = None
    rewriter = None
    lock = threading.Lock()

    exclusion_articles = set()
    exclusion_categories = set()
    inclusion_list = set()

    expected_articles = set()
    expected_categories = set()

    paused_until = None

    @staticmethod
    def set_debug(value):
        Global.debug = value
        level = logging.DEBUG if value else logging.INFO
        Global.logger.setLevel(level)
        for handler in Global.logger.handlers:
            handler.setLevel(level)

    @staticmethod
    def pause():
        # consider it a consequence of concurrent call.
        # await initial pause call expiration
        if Global.paused_until:
            return
        Global.logger.warning("PAUSING requests for 15min")
        Global.paused_until = datetime.datetime.now() + datetime.timedelta(minutes=15)

    @staticmethod
    def await_pause():
        # quick exit when not paused
        if not Global.paused_until:
            return

        # disable pause mode if it's in the past
        now = datetime.datetime.now()
        try:
            until = (Global.paused_until - now).total_seconds()
            if until <= 0:
                Global.paused_until = None
        except TypeError:
            # should paused_until be set to None already
            return

        # block current thread (every seconds to allow interrupts)
        try:
            for _ in range(until):
                time.sleep(1)
        except TypeError:
            # should paused_until be set to None already
            return

    @staticmethod
    def setup():
        # order matters are there are references between them

        # images handled on a different queue.
        # mostly network I/O to retrieve and/or upload image.
        # if not in S3 bucket, convert/optimize webp image
        # svg images, stored but not optimized
        from .executor import Executor

        Global.img_executor = Executor(
            queue_size=20,
            nb_workers=10,
            prefix="IMG-T-",
        )

        # without_videos means without Youtube videos but there are still plenty
        # of regular videos for animations.
        # We use a single video worker for videos if Youtube is enabled to prevent
        # blacklisting of the host IP by Youtube
        # this should be smarter in processing non-youtube videos in parallel and
        # limit youtube ones to a single worker in every cases
        Global.video_executor = Executor(
            queue_size=20,
            nb_workers=10 if Global.conf.without_videos else 1,
            prefix="VID-T-",
        )

        from .imager import Imager

        Global.imager = Imager()

        from .videos import VideoGrabber

        Global.vidgrabber = VideoGrabber()

        from .rewriter import Rewriter

        Global.rewriter = Rewriter()

        Global.creator = Creator(
            filename=Global.conf.output_dir.joinpath(Global.conf.fname),
            main_path=DEFAULT_HOMEPAGE,
            favicon_path="illustration",
            language=Global.conf.language["iso-639-3"],
            ignore_duplicates=True,
            title=Global.conf.title,
            description=Global.conf.description,
            creator=Global.conf.author,
            publisher=Global.conf.publisher,
            name=Global.conf.name,
            tags=";".join(Global.conf.tags),
            date=datetime.date.today(),
        ).config_verbose(True)


class GlobalMixin:
    @property
    def conf(self):
        return Global.conf

    @property
    def metadata(self):
        return Global.metadata

    @property
    def creator(self):
        return Global.creator

    @property
    def lock(self):
        return Global.lock

    @property
    def imager(self):
        return Global.imager

    @property
    def vidgrabber(self):
        return Global.vidgrabber

    @property
    def executor(self):
        return Global.executor

    @property
    def rewriter(self):
        return Global.rewriter

    @property
    def inclusion_list(self):
        return Global.inclusion_list

    @property
    def exclusion_articles(self):
        return Global.exclusion_articles

    @property
    def exclusion_categories(self):
        return Global.exclusion_categories

    @property
    def expected_articles(self):
        return Global.expected_articles

    @property
    def expected_categories(self):
        return Global.expected_categories

    @property
    def session(self):
        return Global.session


logger = Global.logger
