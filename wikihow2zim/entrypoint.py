# -*- coding: utf-8 -*-

import argparse
import os
import sys

from .constants import NAME, SCRAPER, URLS
from .shared import Global, logger


def main():
    parser = argparse.ArgumentParser(
        prog=NAME,
        description="Scraper to create ZIM files wikihow articles",
    )

    parser.add_argument(
        "--language",
        choices=URLS.keys(),
        required=True,
        help="wikiHow website to build from",
        dest="lang_code",
    )

    parser.add_argument(
        "--output",
        help="Output folder for ZIM file",
        default="/output",
        dest="_output_dir",
    )

    parser.add_argument(
        "--name",
        help="ZIM name. Used as identifier and filename (date will be appended). "
        "Constructed from language if not supplied",
    )

    parser.add_argument(
        "--title", help="Custom title for your ZIM. Wikihow homepage title otherwise"
    )

    parser.add_argument(
        "--description",
        help="Custom description for your ZIM. "
        "Wikihow homepage description (meta) otherwise",
    )

    parser.add_argument(
        "--icon",
        help="Custom icon for your ZIM (path or URL). " "wikiHow square logo otherwise",
    )

    parser.add_argument(
        "--creator",
        help="Name of content creator. “wikiHow” otherwise",
        dest="author",
    )

    parser.add_argument(
        "--publisher", help="Custom publisher name (ZIM metadata). “openZIM” otherwise"
    )

    parser.add_argument(
        "--tag",
        help="Add tag to the ZIM file. "
        "_category:wikihow and wikihow added automatically. Use --tag several times or "
        "separate with `;`",
        default=[],
        action="append",
    )

    parser.add_argument(
        "--zim-file",
        help="ZIM file name (based on --name if not provided)",
        dest="fname",
    )

    parser.add_argument(
        "--category",
        help="Only scrape this category (can be specified multiple times). "
        "Use URL-ID of the Category "
        "(after the colon `:` in the URL). "
        "Add a slash after Category to request it without recursion",
        dest="categories",
        action="append",
    )

    parser.add_argument(
        "--low-quality",
        help="Use lower-quality, smaller file-size video encode",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--without-videos",
        help="Don't include the video blocks (Youtube hosted). Most are copyrighted",
        action="store_true",
        default=False,
        dest="without_videos",
    )

    parser.add_argument(
        "--without-external-links",
        help="Don't include external links",
        action="store_true",
        default=False,
        dest="without_external_links",
    )

    parser.add_argument(
        "--exclude",
        help="Path or URL to a text file listing Article ID or `Category:` prefixed "
        "Category IDs to exclude from the scrape. Lines starting with # are ignored",
        dest="exclude",
    )

    parser.add_argument(
        "--optimization-cache",
        help="URL with credentials to S3 for using as optimization cache",
        dest="s3_url_with_credentials",
    )

    parser.add_argument(
        "--debug", help="Enable verbose output", action="store_true", default=False
    )

    parser.add_argument(
        "--tmp-dir",
        help="Path to create temp folder in. Used for building ZIM file. "
        "Videos are stored and re-encoded there.",
        default=os.getenv("TMPDIR", "."),
        dest="_tmp_dir",
    )

    parser.add_argument(
        "--keep",
        help="Don't remove build folder on start (for debug/devel)",
        default=False,
        action="store_true",
        dest="keep_build_dir",
    )

    parser.add_argument(
        "--build-in-tmp",
        help="Use --tmp-dir value as workdir. Otherwise, a unique sub-folder "
        "is created inside it. Useful to reuse downloaded files (debug/devel)",
        default=False,
        action="store_true",
        dest="build_dir_is_tmp_dir",
    )

    parser.add_argument(
        "--delay",
        help="Add this delay (seconds) before each request to please "
        "wikiHow servers. Can be fractions. Defaults to 0: no delay",
        type=float,
    )

    parser.add_argument(
        "--skip-dom-check",
        help="[dev] Don't perform DOM Integrity Checks on start",
        default=False,
        action="store_true",
        dest="skip_dom_check",
    )

    parser.add_argument(
        "--skip-footer-links",
        help="[dev] Don't scrape footer links",
        default=False,
        action="store_true",
        dest="skip_footer_links",
    )

    parser.add_argument(
        "--skip-relateds",
        help="[dev] Don't fetch related articles from found articles",
        default=False,
        action="store_true",
        dest="skip_relateds",
    )

    parser.add_argument(
        "--single-article",
        help="[dev] Don't scrape categories, just that single article instead",
        dest="single_article",
    )

    parser.add_argument(
        "--stats-filename",
        help="Path to store the progress JSON file to.",
        dest="stats_filename",
    )

    parser.add_argument(
        "--version",
        help="Display scraper version and exit",
        action="version",
        version=SCRAPER,
    )

    args = parser.parse_args()
    Global.set_debug(args.debug)

    from .scraper import wikihow2zim

    try:
        scraper = wikihow2zim(**dict(args._get_kwargs()))
        sys.exit(scraper.run())
    except Exception as exc:
        logger.error(f"FAILED. An error occurred: {exc}")
        if args.debug:
            logger.exception(exc)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
