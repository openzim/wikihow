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
        "-l",
        "--language",
        help="Choose the language (en, de, fr ...)"
    )

    parser.add_argument(
        "-c",
        "--commons",
        help="commons"
    )

    parser.add_argument(
        "--s3",
        help="s3"
    )

    parser.add_argument(
        "-- low-quality",
        help="low quality"
    )

    parser.add_argument(
        "-- no-external-links",
        help="no external links"
    )

    parser.add_argument(
        "-d",
        "--debug", 
        help="Enable verbose output", 
        action="store_true", 
        default=False
    )

    args = parser.parse_args()
    print(args)
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