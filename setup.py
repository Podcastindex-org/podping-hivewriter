# -*- coding: utf-8 -*-
from setuptools import setup

package_dir = {"": "src"}

packages = [
    "podping_hivewriter",
    "podping_hivewriter.cli",
    "podping_hivewriter.models",
    "podping_hivewriter.schema",
]

package_data = {"": ["*"]}

install_requires = [
    "asgiref>=3.4,<4.0",
    "capnpy>=0.9.0,<0.10.0",
    "cffi>=1.14.5,<2.0.0",
    "lighthive>=0.3.0,<0.4.0",
    "pydantic>=1.9.0,<2.0.0",
    "rfc3987>=1.3.8,<2.0.0",
    "single-source>=0.2.0,<0.3.0",
    "typer[all]>=0.3.2,<0.4.0",
]

extras_require = {"server": ["pyzmq>=22.1.0,<23.0.0"]}

entry_points = {"console_scripts": ["podping = podping_hivewriter.cli.podping:app"]}

setup_kwargs = {
    "name": "podping-hivewriter",
    "version": "1.1.0-beta.3",
    "description": "This is a tool used to submit RFC 3987-compliant International Resource Identifiers as a Podping notification on the Hive blockchain.",
    "long_description": "# podping-hivewriter\nThe Hive writer component of podping. You will need a Hive account, see section [Hive account and Authorization](#hive-account) below.\n\n## CLI Install\n\nThe following have been tested on Linux and macOS.  However, Windows should work also.  If you have issues on Windows we highly recommend the [Windows Subsystem for Linux](https://docs.microsoft.com/en-us/windows/wsl/) and/or Docker.\n\n### Using [pipx](https://pypa.github.io/pipx/) (preferred over pip)\n```shell\npipx install podping-hivewriter\n```\n\n### Using pip\n```shell\npip install --user podping-hivewriter\n```\n\n### Installing the server\n\nIf you'd like to install the server component, it's hidden behind the extra flag `server`.  This is to make it easier to install only the `write` CLI component `podping-hivewriter` on non-standard systems without a configured development enviornment.\n\n```shell\npipx install podping-hivewriter[server]\n```\n\nMake sure you have `~/.local/bin/` on your `PATH`.\n\nSee the dedicated [CLI docs](CLI.md) for more information.\n\n## Container\n\nThe container images are hosted on [Docker Hub](https://hub.docker.com/r/podcastindexorg/podping-hivewriter).  Images are currently based on Debian bullseye-based Python 3.9 with the following architectures: `amd64`, `i386`, `arm64`, `armv7`, `armv6`\n\n### docker-compose\n\n```yaml\nversion: '2.0'\nservices:\n  podping-hivewriter:\n    image: podcastindexorg/podping-hivewriter\n    restart: always\n    ports:\n      - \"9999:9999\"\n    environment:\n      - PODPING_HIVE_ACCOUNT=<account>\n      - PODPING_HIVE_POSTING_KEY=<posting-key>\n      - PODPING_LISTEN_IP=0.0.0.0\n      - PODPING_LISTEN_PORT=9999\n      - PODPING_LIVETEST=false\n      - PODPING_DRY_RUN=false\n      - PODPING_STATUS=true\n      - PODPING_IGNORE_CONFIG_UPDATES=false\n      - PODPING_I_KNOW_WHAT_IM_DOING=false\n      - PODPING_DEBUG=false\n```\n\nAssuming you just copy-pasted without reading, the above will fail at first.  As noted in the [server command documentation](https://github.com/Podcastindex-org/podping-hivewriter/blob/main/CLI.md#podping-server):\n\n>WARNING: DO NOT run this on a publicly accessible host. There currently is NO authentication required to submit to the server. Set to * or 0.0.0.0 for all interfaces.\n\nAs all Docker installations vary, we set `0.0.0.0` as the listen IP for connectivity.  This doesn't affect the IP address docker listens on when we tell it to pass port `9999` through to the container.  If you understand the consequences of this, set `PODPING_I_KNOW_WHAT_IM_DOING` to `true`.\n\n### Building the image with Docker\n\nLocally build the podping-hivewriter container with a \"develop\" tag\n\n```shell\ndocker build -t podping-hivewriter:develop .\n```\n\n\n### Running the image\n\nRun the locally built image in a container, passing local port 9999 to port 9999 in the container.\nENV variables can be passed to docker with `--env-file` option after modifying the `.env.EXAMPLE` file and renaming it to `.env`\n\n```shell\ndocker run --rm -p 9999:9999 --env-file .env --name podping podping-hivewriter:develop\n```\n\nRunning with command line options, like `--dry-run` for example, add them with the full podping command.\nSettings can also be passed with the `-e` option for Docker.  Note, we leave out `-p 9999:9999` here because we're not running the server.\n\n```shell\ndocker run --rm \\\n    -e PODPING_HIVE_ACCOUNT=<account> \\\n    -e PODPING_HIVE_POSTING_KEY=<posting-key> \\\n    podping-hivewriter:develop \\\n    podping --dry-run write https://www.example.com/feed.xml\n```\n\nAs another example for running a server, to run in *detached* mode, note the `-d` in the `docker run` options. Also note that `client` or `server` must come *after* the command line options for `podping`:\n```shell\ndocker run --rm -d \\\n    -p 9999:9999 --env-file .env \\\n    --name podping podping-hivewriter:develop \\\n    podping --livetest server\n```\n\nOne running you can view and follow the live output with:\n```shell\ndocker logs podping -f\n```\n\nSee the [CLI docs](https://github.com/Podcastindex-org/podping-hivewriter/blob/main/CLI.md) for default values.\n\n## Development\n\nYou'll need a few extras:\n\n1. [capnproto](https://capnproto.org/). On a Mac: `brew instal capnp`\n2. [Poetry](https://python-poetry.org/docs/)\n\n\nWe use [poetry](https://python-poetry.org/) for dependency management.  Once you have it, clone this repo and run:\n\n```shell\npoetry install\n```\n\nThen to switch to the virtual environment, use:\n\n```shell\npoetry shell\n```\nMake sure you have a the environment variables `PODPING_HIVE_ACCOUNT` and `PODPING_HIVE_POSTING_KEY` set.\n\nAfter that you should be able to run the `podping` command or run the tests:\n\n```shell\npytest\n```\n\nTo run all tests, make sure to set the necessary environment variables for your Hive account.  This can take many minutes:\n\n```shell\npytest --runslow\n```\n\n## Hive account\n\nIf you need a Hive account, please download the [Hive Keychain extension for your browser](https://hive-keychain.com/) then use this link to get your account from [https://HiveOnboard.com?ref=podping](https://hiveonboard.com?ref=podping). You will need at least 20 Hive Power \"powered up\" to get started (worth around $10). Please contact [@brianoflondon](https://peakd.com/@brianoflondon) brian@podping.org if you need assistance getting set up.\n\nIf you use the [Hiveonboard]((https://hiveonboard.com?ref=podping)) link `podping` will **delegate** enough Hive Power to get you started.\n\n### Permissions and Authorization\n\nYou don't need permission, but you do need to tell `podping` that you want to send valid `podpings`:\n\n- Hive is a so-called \"permissionless\" blockchain.  Once you have a Hive Account and a minimal amount of Hive Power, that account can post to Hive, including sending `podpings`.\n\n- Nobody can block any valid Hive Account from sending and nobody can help you if you lose your keys.\n\n- Whilst anyone can post `podpings` to Hive, there is a need to register your Hive Accountname for those `podpings` to be recognized by all clients.  This is merely a spam-prevention measure and clients may choose to ignore it.\n\n- Please contact new@podping.org or send a Hive Transfer to [@podping](https://peakd.com/@podping) to have your account validated.\n\n- Side note on keys: `podping` uses the `posting-key` which is the lowest value of the four Hive keys (`owner`, `active`, `memo`, `posting` and there is usually a `master password` which can generate all the keys). That is not to say that losing control of it is a good idea, but that key is not authorized to make financially important transfers. It can, however, post public information so should be treated carefully and kept secure.\n\nFor a [comprehensive explanation of Hive and Podping, please see this post](https://peakd.com/podping/@brianoflondon/podping-and-podcasting-20-funding-to-put-hive-at-the-center-of-global-podcasting-infrastructure).",
    "author": "Alecks Gates",
    "author_email": "alecks@podping.org",
    "maintainer": "Alecks Gates",
    "maintainer_email": "alecks@podping.org",
    "url": "http://podping.org/",
    "package_dir": package_dir,
    "packages": packages,
    "package_data": package_data,
    "install_requires": install_requires,
    "extras_require": extras_require,
    "entry_points": entry_points,
    "python_requires": ">=3.8,<4.0",
}
from build import *

build(setup_kwargs)

setup(**setup_kwargs)
