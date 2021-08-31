#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import io
import re
import urllib.parse
from typing import Optional

import youtube_dl
from kiwixstorage import KiwixStorage, NotFoundError
from zimscraperlib.video.encoding import reencode
from zimscraperlib.video.presets import VideoWebmHigh, VideoWebmLow

from .constants import VIDEOS_ENCODER_VERSION
from .shared import Global
from .utils import get_digest, get_version_ident_for, mormalize_youtube_url

logger = Global.logger


class VideoGrabber:
    def __init__(self):
        self.aborted = False
        # list of source URLs that we've processed and added to ZIM
        self.handled = set()
        self.nb_requested = 0
        self.nb_done = 0

        Global.video_executor.start()

    @property
    def videos_dir(self):
        return Global.conf.build_dir.joinpath("videos")

    def abort(self):
        """request videor to cancel processing of futures"""
        self.aborted = True

    def get_url(self, url: str):

        is_youtube = False
        if "https://www.youtube.com/" in url:
            url = mormalize_youtube_url(url)
            is_youtube = True

        return urllib.parse.urlparse(url), is_youtube

    def get_video_data(self, url: str, is_youtube: bool) -> io.BytesIO:
        preset = VideoWebmLow() if Global.conf.low_quality else VideoWebmHigh()
        audext, vidext = ("webm", "webm")
        video_format = "webm"
        digest = get_digest(url)
        options = {
            "cachedir": self.videos_dir,
            "writethumbnail": False,
            "writesubtitles": False,
            "allsubtitles": False,
            "writeautomaticsub": False,
            "subtitlesformat": "vtt",
            "keepvideo": False,
            "ignoreerrors": False,
            "retries": 20,
            "fragment-retries": 50,
            "skip-unavailable-fragments": True,
            "outtmpl": str(self.videos_dir.joinpath(digest + ".%(ext)s")),
            "preferredcodec": video_format,
            "format": f"best[ext={vidext}]/bestvideo[ext={vidext}]+"
            f"bestaudio[ext={audext}]/best",
            "y2z_videos_dir": self.videos_dir,
            "nocheckcertificate": True,
        }
        with youtube_dl.YoutubeDL(options) as ydl:
            ydl.download([url])

        files = [
            p
            for p in self.videos_dir.iterdir()
            if p.stem == digest and p.suffix not in (".jpg", ".webp")
        ]

        if len(files) == 0:
            # logger.info(list(self.videos_dir.iterdir()))
            logger.error(f"Video file missing in {self.videos_dir} for {url}")
            logger.debug(list(self.videos_dir.iterdir()))
            raise FileNotFoundError(f"Missing video file in {self.videos_dir}")
        if len(files) > 1:
            logger.warning(
                f"Multiple video file candidates for {url} in {self.videos_dir}."
                f" Picking {files[0]} out of {files}"
            )
        src_path = files[0]

        if not Global.conf.low_quality and src_path.suffix[1:] == video_format:
            return src_path

        dst_path = src_path.with_suffix(f".{video_format}")
        reencode(
            src_path,
            dst_path,
            preset.to_ffmpeg_args(),
            delete_src=False,
            failsafe=False,
        )
        # print(dst_path)
        return dst_path

    def get_s3_key_for(self, url: str) -> str:
        """S3 key to use for that url"""
        return re.sub(r"^(https?)://", r"\1/", url)

    def defer(
        self,
        url: str,
        path: Optional[str] = None,
    ) -> str:
        """request full processing of url, returning in-zim path immediately"""

        # find actual URL should it be from a provider
        logger.debug(f"deferring {url=} {path=}")
        try:
            url, is_youtube = self.get_url(url)
        except Exception:
            logger.warning(f"Can't parse video URL `{url}`. Skipping")
            return

        if url.scheme not in ("http", "https"):
            logger.warning(f"Not supporting video URL `{url.geturl()}`. Skipping")
            return

        # skip processing if we already processed it or have it in pipe
        digest = get_digest(url.geturl())
        if path is None:
            path = f"videos/{digest}"

        if digest in self.handled:
            logger.debug(f"URL `{url.geturl()}` already processed.")
            return path

        # record that we are processing this one
        self.handled.add(digest)
        self.nb_requested += 1

        Global.video_executor.submit(
            self.process_video,
            url=url,
            is_youtube=is_youtube,
            path=path,
            dont_release=True,
        )

        return path

    def once_done(self):
        """default callback for single video processing"""
        self.nb_done += 1
        logger.debug(f"Videos {self.nb_done}/{self.nb_requested}")

    def process_video(self, url: str, is_youtube: bool, path) -> str:
        """download video from url or S3 and add to Zim at path. Upload if req."""

        if self.aborted:
            return

        # just download, optimize and add to ZIM if not using S3
        if not Global.conf.s3_url:
            with Global.lock:
                Global.creator.add_item_for(
                    path=path,
                    fpath=self.get_video_data(url.geturl(), is_youtube),
                    delete_fpath=True,
                    callback=self.once_done,
                )
            return path

        # we are using S3 cache
        if is_youtube:
            ident = "1"
        else:
            ident = get_version_ident_for(url.geturl())
            if ident is None:
                logger.error(f"Unable to query {url.geturl()}. Skipping")
                return path

        key = self.get_s3_key_for(url.geturl())
        s3_storage = KiwixStorage(Global.conf.s3_url)
        meta = {"ident": ident, "encoder_version": str(VIDEOS_ENCODER_VERSION)}

        download_failed = False  # useful to trigger reupload or not
        try:
            logger.debug(f"Attempting download of S3::{key} into ZIM::{path}")
            fileobj = io.BytesIO()
            s3_storage.download_matching_fileobj(key, fileobj, meta=meta)
        except NotFoundError:
            # don't have it, not a donwload error. we'll upload after processing
            pass
        except Exception as exc:
            logger.error(f"failed to download {key} from cache: {exc}")
            logger.exception(exc)
            download_failed = True
        else:
            with Global.lock:
                Global.creator.add_item_for(
                    path=path,
                    content=fileobj.getvalue(),
                    callback=self.once_done,
                )
            return path

        # we're using S3 but don't have it or failed to download
        try:
            fpath = self.get_video_data(url.geturl(), is_youtube)
        except Exception as exc:
            logger.error(f"Failed to download/convert/optim source  at {url.geturl()}")
            logger.exception(exc)
            return path

        with Global.lock:
            Global.creator.add_item_for(
                path=path,
                fpath=fpath,
                delete_fpath=True,
                callback=self.once_done,
            )

        # only upload it if we didn't have it in cache
        if not download_failed:
            logger.debug(f"Uploading {url.geturl()} to S3::{key} with {meta}")
            try:
                s3_storage.upload_file(fpath=fpath, key=key, meta=meta)
            except Exception as exc:
                logger.error(f"{key} failed to upload to cache: {exc}")

        return path
