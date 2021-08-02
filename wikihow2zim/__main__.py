# -*- coding: utf-8 -*-

import sys
import pathlib


def main():
    # allows running it from source using python wikihow2zim
    sys.path = [str(pathlib.Path(__file__).parent.parent.resolve())] + sys.path

    from wikihow2zim.entrypoint import main as entry

    entry()


if __name__ == "__main__":
    main()
