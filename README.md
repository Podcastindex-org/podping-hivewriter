# podping-hivewriter
The Hive writer component of podping. You will need a Hive account, see section [Hive account and Authorization](#hive-account) below.

## CLI Install

The following have been tested on Linux and macOS.  However, Windows should work also.  If you have issues on Windows we highly recommend the [Windows Subsystem for Linux](https://docs.microsoft.com/en-us/windows/wsl/) and/or Docker.

### Using [pipx](https://pypa.github.io/pipx/) (preferred over pip)
```shell
pipx install podping-hivewriter
```

### Using pip
```shell
pip install --user podping-hivewriter
```

### Installing the server

If you'd like to install the server component, it's hidden behind the extra flag `server`.  This is to make it easier to install only the `write` CLI component `podping-hivewriter` on non-standard systems without a configured development enviornment.

```shell
pipx install podping-hivewriter[server]
```

Make sure you have `~/.local/bin/` on your `PATH`.

See the dedicated [CLI docs](CLI.md) for more information.

## Container

The container images are hosted on [Docker Hub](https://hub.docker.com/r/podcastindexorg/podping-hivewriter).  Images are currently based on Debian bullseye-based Python 3.9 with the following architectures: `amd64`, `i386`, `arm64`, `armv7`, `armv6`

### docker-compose

```yaml
version: '2.0'
services:
  podping-hivewriter:
    image: podcastindexorg/podping-hivewriter
    restart: always
    ports:
      - "9999:9999"
    environment:
      - PODPING_HIVE_ACCOUNT=<account>
      - PODPING_HIVE_POSTING_KEY=<posting-key>
      - PODPING_LISTEN_IP=0.0.0.0
      - PODPING_LISTEN_PORT=9999
      - PODPING_LIVETEST=false
      - PODPING_DRY_RUN=false
      - PODPING_STATUS=true
      - PODPING_IGNORE_CONFIG_UPDATES=false
      - PODPING_I_KNOW_WHAT_IM_DOING=false
      - PODPING_DEBUG=false
```

Assuming you just copy-pasted without reading, the above will fail at first.  As noted in the [server command documentation](https://github.com/Podcastindex-org/podping-hivewriter/blob/main/CLI.md#podping-server):

>WARNING: DO NOT run this on a publicly accessible host. There currently is NO authentication required to submit to the server. Set to * or 0.0.0.0 for all interfaces.

As all Docker installations vary, we set `0.0.0.0` as the listen IP for connectivity.  This doesn't affect the IP address docker listens on when we tell it to pass port `9999` through to the container.  If you understand the consequences of this, set `PODPING_I_KNOW_WHAT_IM_DOING` to `true`.

### Building the image with Docker

Locally build the podping-hivewriter container with a "develop" tag

```shell
docker build -t podping-hivewriter:develop .
```


### Running the image

Run the locally built image in a container, passing local port 9999 to port 9999 in the container.
ENV variables can be passed to docker with `--env-file` option after modifying the `.env.EXAMPLE` file and renaming it to `.env`

```shell
docker run --rm -p 9999:9999 --env-file .env --name podping podping-hivewriter:develop
```

Running with command line options, like `--dry-run` for example, add them with the full podping command.
Settings can also be passed with the `-e` option for Docker.  Note, we leave out `-p 9999:9999` here because we're not running the server.

```shell
docker run --rm \
    -e PODPING_HIVE_ACCOUNT=<account> \
    -e PODPING_HIVE_POSTING_KEY=<posting-key> \
    podping-hivewriter:develop \
    podping --dry-run write https://www.example.com/feed.xml
```

As another example for running a server, to run in *detached* mode, note the `-d` in the `docker run` options. Also note that `client` or `server` must come *after* the command line options for `podping`:
```shell
docker run --rm -d \
    -p 9999:9999 --env-file .env \
    --name podping podping-hivewriter:develop \
    podping --livetest server
```

One running you can view and follow the live output with:
```shell
docker logs podping -f
```

See the [CLI docs](https://github.com/Podcastindex-org/podping-hivewriter/blob/main/CLI.md) for default values.

## Development

You'll need a few extras:

1. [capnproto](https://capnproto.org/). On a Mac: `brew instal capnp`
2. [Poetry](https://python-poetry.org/docs/)


We use [poetry](https://python-poetry.org/) for dependency management.  Once you have it, clone this repo and run:

```shell
poetry install
```

Then to switch to the virtual environment, use:

```shell
poetry shell
```
Make sure you have a the environment variables `PODPING_HIVE_ACCOUNT` and `PODPING_HIVE_POSTING_KEY` set.

After that you should be able to run the `podping` command or run the tests:

```shell
pytest
```

To run all tests, make sure to set the necessary environment variables for your Hive account.  This can take many minutes:

```shell
pytest --runslow
```

## Hive account

If you need a Hive account, please download the [Hive Keychain extension for your browser](https://hive-keychain.com/) then use this link to get your account from [https://HiveOnboard.com?ref=podping](https://hiveonboard.com?ref=podping). You will need at least 20 Hive Power "powered up" to get started (worth around $10). Please contact [@brianoflondon](https://peakd.com/@brianoflondon) brian@podping.org if you need assistance getting set up.

If you use the [Hiveonboard]((https://hiveonboard.com?ref=podping)) link `podping` will **delegate** enough Hive Power to get you started. If for any reason Hiveonboard is not giving out free accounts, please contact [@brianoflondon](https://peakd.com/@brianoflondon) either on [PodcastIndex Social](https://podcastindex.social/invite/U2m6FY3T) or [Telegram](https://t.me/brianoflondon).

### Permissions and Authorization

You don't need permission, but you do need to tell `podping` that you want to send valid `podpings`:

- Hive is a so-called "permissionless" blockchain.  Once you have a Hive Account and a minimal amount of Hive Power, that account can post to Hive, including sending `podpings`.

- Nobody can block any valid Hive Account from sending and nobody can help you if you lose your keys.

- Whilst anyone can post `podpings` to Hive, there is a need to register your Hive Accountname for those `podpings` to be recognized by all clients.  This is merely a spam-prevention measure and clients may choose to ignore it.

- Please contact new@podping.org or send a Hive Transfer to [@podping](https://peakd.com/@podping) to have your account validated.

- Side note on keys: `podping` uses the `posting-key` which is the lowest value of the four Hive keys (`owner`, `active`, `memo`, `posting` and there is usually a `master password` which can generate all the keys). That is not to say that losing control of it is a good idea, but that key is not authorized to make financially important transfers. It can, however, post public information so should be treated carefully and kept secure.

For a [comprehensive explanation of Hive and Podping, please see this post](https://peakd.com/podping/@brianoflondon/podping-and-podcasting-20-funding-to-put-hive-at-the-center-of-global-podcasting-infrastructure).