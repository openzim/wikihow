# -*- coding: utf-8 -*-

import sys
import argparse

from .constants import NAME, SCRAPER, setDebug, getLogger


def main():
    parser = argparse.ArgumentParser(
        prog=NAME,
        description="Scraper to create ZIM files wikihow articles",
    )

    parser.add_argument(
        "--language",
        choices=["en", "de", "fr"],
        default="en",
        help="Choose the language (en, de, fr ...)",
    )

    parser.add_argument(
        "--name",
        help="ZIM name. Used as identifier and filename (date will be appended)",
        required=True,
    )

    parser.add_argument(
        "--title",
        help="Custom title for your ZIM. Wikihow article title otherwise",
    )

    parser.add_argument(
        "--description",
        help="Custom description for your ZIM. Wikihow article description otherwise",
    )

    parser.add_argument(
        "--publisher", help="Custom publisher name (ZIM metadata). “OpenZIM” otherwise"
    )

    parser.add_argument(
        "--tags",
        help="List of comma-separated Tags for the ZIM file. "
        "category:other, kolibri, and _videos:yes added automatically",
    )

    parser.add_argument(
        "--output",
        help="Output folder for ZIM file",
        default="/output",
        dest="output_dir",
    )

    parser.add_argument(
        "--tmp-dir",
        help="Path to create temp folder in. Used for building ZIM file. "
        "Receives all data (storage space)",
    )

    parser.add_argument(
        "--zim-file",
        help="ZIM file name (based on --name if not provided)",
        dest="fname",
    )

    parser.add_argument(
        "--keep",
        help="Don't remove build folder on start (for debug/devel)",
        default=False,
        action="store_true",
        dest="keep_build_dir",
    )

    parser.add_argument(
        "--version",
        help="Display scraper version and exit",
        action="version",
        version=SCRAPER,
    )

    parser.add_argument(
        "--optimization-cache",
        help="URL with credentials to S3 for using as optimization cache",
        dest="s3_url_with_credentials",
    )

    parser.add_argument(
        "--low-quality",
        help="Use lower-quality, smaller file-size video encode",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--no-external-links",
        help="Don't include external links",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--debug", help="Enable verbose output", action="store_true", default=False
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
