# -*- coding: utf-8 -*-

import pathlib
import subprocess
import sys

from setuptools import setup

root_dir = pathlib.Path(__file__).parent


def read(*names, **kwargs):
    with open(root_dir.joinpath(*names), "r") as fh:
        return fh.read()


print("Installing a fork of pywikiapi")
subprocess.run(
    [
        sys.executable,
        "-m",
        "pip",
        "install",
        [
            line.strip()
            for line in read("requirements.txt").splitlines()
            if "/pywikiapi" in line
        ][-1],
    ],
    check=True,
)

print("Downloading JS dependencies...")
subprocess.run([str(root_dir.joinpath("get_js_deps.sh").resolve())], check=True)


setup(
    name="wikihow2zim",
    version=read("wikihow2zim", "VERSION").strip(),
    description="Make ZIM file from WikiHow articles",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    author="Kiwix Team",
    author_email="dev@kiwix.org",
    url="https://kiwix.org/",
    keywords="kiwix zim offline wikihow",
    license="GPLv3+",
    packages=["wikihow2zim"],
    install_requires=[
        line.strip()
        for line in read("requirements.txt").splitlines()
        if not line.strip().startswith("#") and not line.startswith("https://")
    ],
    zip_safe=False,
    include_package_data=True,
    package_data={"": ["VERSION", "templates/*", "assets/*"]},
    entry_points={
        "console_scripts": [
            "wikihow2zim=wikihow2zim.__main__:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    ],
    python_requires=">=3.8",
)
