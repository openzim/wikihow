# -*- coding: utf-8 -*-

options = [
    "commons",
    "debug",
    "language",
    "low_quality",
    "no_external_links",
    "s3_url_with_credentials",
]

class wikihow2zim:
    def __init__(self, **kwargs):
        print("kwargs", kwargs)

        for option in options:
            if option not in kwargs:
                raise ValueError(f"Missing parameter `{option}`")

        self.commons = kwargs.get("commons")
        self.debug = kwargs.get("debug")
        self.language = kwargs.get("language")
        self.low_quality = kwargs.get("low_quality")
        self.no_external_links = kwargs.get("no_external_links")
        self.s3_url_with_credentials = kwargs.get("s3_url_with_credentials")

    def run(self):
        print("self", self.__dict__)