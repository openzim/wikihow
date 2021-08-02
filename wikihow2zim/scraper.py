# -*- coding: utf-8 -*-

options = [
    "language",
    "name",
    "title",
    "description",
    "publisher",
    "tags",
    "output_dir",
    "tmp_dir",
    "fname",
    "keep_build_dir",
    "low_quality",
    "no_external_links",
    "s3_url_with_credentials",
    "debug",
]


class wikihow2zim:
    def __init__(self, **kwargs):

        for option in options:
            if option not in kwargs:
                raise ValueError(f"Missing parameter `{option}`")

        for option in options:
            setattr(self, option, kwargs[option])

    def run(self):
        pass
