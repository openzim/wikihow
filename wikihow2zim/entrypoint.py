# -*- coding: utf-8 -*-

import os
import sys
import argparse

from .constants import NAME, SCRAPER, URLS, setDebug, getLogger


def main():
    parser = argparse.ArgumentParser(
        prog=NAME,
        description="Scraper to create ZIM files wikihow articles",
    )

    parser.add_argument(
        "--language",
        choices=URLS.keys(),
        required=True,
        help="Wikihow website to build from",
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
        help="ZIM name. Used as identifier and filename (date will be appended)",
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
        "--publisher", help="Custom publisher name (ZIM metadata). “OpenZIM” otherwise"
    )

    parser.add_argument(
        "--tag",
        help="Add tag to the ZIM file. "
        "category:other and wikihow added automatically",
        default=["  _category:other", "wikihow"],
        action="append",
    )

    parser.add_argument(
        "--zim-file",
        help="ZIM file name (based on --name if not provided)",
        dest="fname",
    )

    parser.add_argument(
        "--category",
        help="Only scrape this category (option can be used multiple times). "
        "Use the URL-ID or the Category "
        "(after the Category: –or equivalent– in the URL",
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
        "--without_external_links",
        help="Don't include external links",
        action="store_true",
        default=False,
        dest="without_external_links",
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
        "--version",
        help="Display scraper version and exit",
        action="version",
        version=SCRAPER,
    )

    args = parser.parse_args()
    setDebug(args.debug)
    logger = getLogger()

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
