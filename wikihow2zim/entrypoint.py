# -*- coding: utf-8 -*-

import sys
import argparse

from .constants import NAME, setDebug, getLogger

def main():
    parser = argparse.ArgumentParser(
        prog=NAME,
        description="Scraper to create ZIM files from Kolibri channels",
    )

    parser.add_argument(
        "--language",
        choices=['en', 'de', 'fr'],
        default='en',
        help="Choose the language (en, de, fr ...)"
    )

    parser.add_argument(
        "--optimization-cache",
        help="URL with credentials to S3 for using as optimization cache",
        dest="s3_url_with_credentials",
    )

    parser.add_argument(
        "--low-quality",
        help="Uses only the `low_res` version of videos if available. "
        "If not, recompresses using agressive compression.",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--no-external-links",
        help="If specified, don't include external links",
        action="store_true",
        default=False
    )

    parser.add_argument(
        "--debug", 
        help="Enable verbose output", 
        action="store_true", 
        default=False
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