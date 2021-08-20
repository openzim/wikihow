# wikihow

`wikihow2zim` is an [OpenZIM](https://github.com/openzim) scraper to create offline versions of [wikiHow](https://www.wikihow.com) websites, in all its supported languages.

[![CodeFactor](https://www.codefactor.io/repository/github/openzim/wikihow/badge)](https://www.codefactor.io/repository/github/openzim/wikihow)
[![Docker](https://img.shields.io/docker/v/openzim/wikihow?label=docker&sort=semver)](https://hub.docker.com/r/openzim/wikihow)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![PyPI version shields.io](https://img.shields.io/pypi/v/wikihow2zim.svg)](https://pypi.org/project/wikihow2zim/)

## Usage

`wikihow2zim` works off a *language version* that you must provide via the `--language` argument. The list of supported languages is visible in the `--help` message.

### Docker

```bash
docker run -v my_dir:/output openzim/wikihow wikihow2zim --help
```

### Python

`wikihow2zim` is a Python3 (**3.6+**) software. If you are not using the [Docker](https://docker.com) image, you are advised to use it in a virtual environment to avoid installing software dependencies on your system.

```bash
python3 -m venv env
source env/bin/activate

# using published version
pip3 install wikihow2zim
wikihow2zim --help

# running from source
python wikihow2zim/ --help
```

Call `deactivate` to quit the virtual environment.

See `requirements.txt` for the list of python dependencies.


## Contributing

**All contributions are welcome!**

Please open an issue on Github and/or submit a Pull-request.

### Guidelines

- Don't take assigned issues. Comment if those get staled.
- If your contribution is far from trivial, open an issue to discuss it first.
- Ensure your code passed [black formatting](https://pypi.org/project/black/), [isort](https://pypi.org/project/isort/) and [flake8](https://pypi.org/project/flake8/) (88 chars)

We have a [pre-commit](https://pre-commit.com) hook ready for you. Install it with `pip install pre-commit && pre-commit install`
