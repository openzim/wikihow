#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import io
import zlib
import urllib.parse
from typing import Union, Iterable, List, Tuple

import bs4
import requests
import cssbeautifier
from pif import get_public_ip
from kiwixstorage import KiwixStorage
from zimscraperlib.download import stream_file

from .shared import Global, logger


def get_url(path: str) -> str:
    """in-source website url for a path"""
    return f"{Global.conf.main_url.geturl()}{path}"


def to_url(value: str) -> str:
    """resolved potentially relative url from in-source link"""
    return value if value.startswith("http") else get_url(value)


def to_rel(url: str) -> Union[None, str]:
    """path from URL if on our main domain, else None"""
    uri = urllib.parse.urlparse(url)
    if uri.netloc != Global.conf.domain:
        return None
    return uri.path


def fetch(path: str) -> str:
    """source text of a path from source website"""
    resp = requests.get(url=get_url(path))
    resp.raise_for_status()
    return resp.text


def get_soup(path: str) -> bs4.BeautifulSoup:
    """an lxml soup of a path on source website"""
    return bs4.BeautifulSoup(fetch(path), "lxml")


def soup_link_finder(elem: bs4.element.Tag) -> bool:
    """bs4's find_all-friendly selector for linked styles in wikiHow"""
    return (
        elem.name == "link"
        and elem.attrs.get("href")
        and (elem.attrs.get("as") == "style" or elem.attrs.get("rel") == "stylesheet")
    )


def get_digest(url: str) -> str:
    """simple digest of an url for mapping purpose"""
    return str(zlib.adler32(url.encode("UTF-8")))


def cat_ident_for(href: str) -> str:
    """decoded name of a category from a link target"""
    return normalize_ident(href.split(":", 1)[1])


def normalize_ident(ident: str) -> str:
    """URL-decoded category identifier"""
    return urllib.parse.unquote(ident)


def article_ident_for(href: str) -> str:
    """decoded name of an article from a link target"""
    return normalize_ident(to_rel(href))[1:]


def parse_css(style: str) -> Tuple[str, List[Tuple[str, str]]]:
    """(css, resources) of transformed CSS string and resources list

    reads a CSS string and returns it transformed
    with url() replaced by offlinable path.

    resources list is list of tuples, each containing the URL to get data from
    and the path to store it at.
    ex: ("http://goto.img/hello.png", "img/hello.png")"""

    output = ""
    resources = []

    def write(line):
        nonlocal output
        output += line + "\n"

    pattern = "url("
    for line in cssbeautifier.beautify(style).split("\n"):
        if pattern not in line:
            write(line)
            continue

        start = line.index(pattern) + len(pattern)
        end = line.index(")")

        # check whether it's quoted or not
        if line[start + 1] in ("'", '"'):
            start += 1
            end -= 1

        url = line[start:end]

        if url.startswith("data:"):
            write(line)
            continue

        path = f"assets/{get_digest(url)}"
        resources.append((url, path))
        # resources are added on same level (assets/xxx) as css itself
        write(line[0:start] + "../" + path + line[end:])

    return output, resources


def first(*args: Iterable[object]) -> object:
    """first non-None value from *args ; fallback to empty string"""
    return next((item for item in args if item is not None), "")


def rebuild_uri(
    uri: urllib.parse.ParseResult,
    scheme: str = None,
    username: str = None,
    password: str = None,
    hostname: str = None,
    port: Union[str, int] = None,
    path: str = None,
    params: str = None,
    query: str = None,
    fragment: str = None,
    failsafe: bool = False,
) -> urllib.parse.ParseResult:
    """new named tuple from uri with requested part updated"""
    try:
        username = first(username, uri.username, "")
        password = first(password, uri.password, "")
        hostname = first(hostname, uri.hostname, "")
        port = first(port, uri.port, "")
        netloc = (
            f"{username}{':' if password else ''}{password}"
            f"{'@' if username or password else ''}{hostname}"
            f"{':' if port else ''}{port}"
        )
        return urllib.parse.urlparse(
            urllib.parse.urlunparse(
                (
                    first(scheme, uri.scheme),
                    netloc,
                    first(path, uri.path),
                    first(params, uri.params),
                    first(query, uri.query),
                    first(fragment, uri.fragment),
                )
            )
        )
    except Exception as exc:
        if failsafe:
            logger.error(
                f"Failed to rebuild "  # lgtm [py/clear-text-logging-sensitive-data]
                f"URI {uri} with {scheme=} {username=} {password=} "
                f"{hostname=} {port=} {path=} "
                f"{params=} {query=} {fragment=} - {exc}"
            )
            return uri
        raise exc


def get_version_ident_for(url: str) -> str:
    """~version~ of the URL data to use for comparisons. Built from headers"""
    try:
        resp = requests.head(url)
        headers = resp.headers
    except Exception:
        logger.warning(f"Unable to HEAD {url}")
        try:
            _, headers = stream_file(
                url=url,
                byte_stream=io.BytesIO(),
                block_size=1,
                only_first_block=True,
            )
        except Exception:
            logger.warning(f"Unable to query image at {url}")
            return

    for header in ("ETag", "Last-Modified", "Content-Length"):
        if headers.get(header):
            return headers.get(header)

    return "-1"


def setup_s3_and_check_credentials(s3_url_with_credentials):
    logger.info("testing S3 Optimization Cache credentials")
    s3_storage = KiwixStorage(s3_url_with_credentials)
    if not s3_storage.check_credentials(
        list_buckets=True, bucket=True, write=True, read=True, failsafe=True
    ):
        logger.error("S3 cache connection error testing permissions.")
        logger.error(f"  Server: {s3_storage.url.netloc}")
        logger.error(f"  Bucket: {s3_storage.bucket_name}")
        logger.error(f"  Key ID: {s3_storage.params.get('keyid')}")
        logger.error(f"  Public IP: {get_public_ip()}")
        raise ValueError("Unable to connect to Optimization Cache. Check its URL.")
    return s3_storage
