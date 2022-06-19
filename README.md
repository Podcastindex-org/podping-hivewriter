# podping-hivewriter
The Hive writer component of Podping. You will need a Hive account, see section [Hive account and Authorization](#hive-account) below.

## What is Podping?

Podping is a mechanism of using decentralized communication to relay notification of updates of RSS feeds that use The Podcast Namespace.  It does so by supplying minimum relevant metadata to consumers to be able to make efficient and actionable decisions, allowing them to decide what to do with given RSS feeds without parsing them ahead of time.

*This* project provides a standardized way of posting a "podping" specifically to the Hive blockcahin.

## Running podping-hivewriter

The project has two modes of running:  `write` mode and `server` mode.

`write` mode is primarily useful for people with a very small number of feeds to publish updates for relatively infrequently (i.e. a few times a day or less).

`server` mode is for hosts (or other services like the Podcast Index's [podping.cloud](https://podping.cloud/)) who publish updates for a significant amount of feeds on a regular basis.  Not that the average small-time podcast can't run it, but it's overkill.  This mode is for efficiency only, as the `server` will batch process feeds as they come in to make the most use of the Hive blockchain.

See the dedicated [CLI docs](CLI.md) for more information on configuration options, including environment variables.

### Container

The container images are hosted on [Docker Hub](https://hub.docker.com/r/podcastindexorg/podping-hivewriter).  Images are currently based on Debian bullseye-based PyPy 3.8 with the following architectures: `amd64`

These images can be run in either `write` or `server` mode and is likely the easiest option for users who do not have experience installing Python packages.

#### Command Line

Running in `write` mode with command line options, like `--dry-run` for example, add them with the full podping command.
Settings can also be passed with the `-e` option for Docker.  Note, we leave out `-p 9999:9999` here because we're not running the server.

```shell
docker run --rm \
    -e PODPING_HIVE_ACCOUNT=<account> \
    -e PODPING_HIVE_POSTING_KEY=<posting-key> \
    docker.io/podcastindexorg/podping-hivewriter \
    --dry-run write https://www.example.com/feed.xml
```

Run in `server` mode, passing local port 9999 to port 9999 in the container.
ENV variables can be passed to docker with `--env-file` option after modifying the `.env.EXAMPLE` file and renaming it to `.env`

```shell
docker run --rm -p 9999:9999 --env-file .env --name podping docker.io/podcastindexorg/podping-hivewriter
```

As another example for running in `server` mode, to run in *detached* mode, note the `-d` in the `docker run` options.  Also note that `write` or `server` must come *after* the command line options for `podping`:
```shell
docker run --rm -d \
    -p 9999:9999 --env-file .env \
    --name podping \
    docker.io/podcastindexorg/podping-hivewriter \
    --livetest server
```

One running you can view and follow the live output with:
```shell
docker logs podping -f
```

See the [CLI docs](https://github.com/Podcastindex-org/podping-hivewriter/blob/main/CLI.md) for default values.


#### docker-compose

```yaml
version: '2.0'
services:
  podping-hivewriter:
    image: docker.io/podcastindexorg/podping-hivewriter
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

This is a temporary measure to limit potential misconfiguration until we fully bundle the `podping.cloud` HTTP front end.  Then again, if you're running this, you're probably Dave.


### CLI Install

The following have been tested on Linux and macOS.  However, Windows should work also.  If you have issues on Windows we highly recommend the [Windows Subsystem for Linux](https://docs.microsoft.com/en-us/windows/wsl/) and/or Docker.

#### Using [pipx](https://pypa.github.io/pipx/) (preferred over pip)
```shell
pipx install podping-hivewriter
```

#### Using pip
```shell
pip install --user podping-hivewriter
```

#### Installing the server

If you'd like to install the server component, it's hidden behind the extra flag `server`.  This is to make it easier to install only the `write` CLI component `podping-hivewriter` on non-standard systems without a configured development enviornment.

```shell
pipx install podping-hivewriter[server]
```

Make sure you have `~/.local/bin/` on your `PATH`.

See the dedicated [CLI docs](CLI.md) for more information.

## Podping reasons

Podping accepts various different "reasons" for publishing updates to RSS feeds:

* `update` -- A general indication that an RSS feed has been updated
* `live` -- An indication that an RSS feed has been updated and a contained [`<podcast:liveItem>`](https://github.com/Podcastindex-org/podcast-namespace/blob/main/docs/1.0.md#live-item) tag's status attribute has been changed to live.
* `liveEnd` -- An indication that an RSS feed has been updated and either the status attribute of an existing [`<podcast:liveItem>`](https://github.com/Podcastindex-org/podcast-namespace/blob/main/docs/1.0.md#live-item) has been changed from live to ended or a [`<podcast:liveItem>`](https://github.com/Podcastindex-org/podcast-namespace/blob/main/docs/1.0.md#live-item) that previously had a status attribute of live has been removed from the feed entirely.

The canonical list of reasons within the scope of this project is [maintained in this schema](https://github.com/Podcastindex-org/podping-hivewriter/blob/main/src/podping_hivewriter/schema/reason.capnp).

## Mediums

Podping accepts various different "mediums" for identifying types of RSS feeds using the Podcast Namespace.  Please check the [`<podcast:medium>`](https://github.com/Podcastindex-org/podcast-namespace/blob/main/docs/1.0.md#medium) specification for the full list.

`podping-hivewriter` *may* lag behind the specification, and if it does, please let us know or submit a pull request.

The canonical list of mediums within the scope of this project is [maintained in this schema](https://github.com/Podcastindex-org/podping-hivewriter/blob/main/src/podping_hivewriter/schema/medium.capnp).

## Development

You'll need a few extras:

1. [capnproto](https://capnproto.org/). Linux: `capnproto` package in your package manager.  On a Mac: `brew instal capnp`
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

To run all tests, make sure to set the necessary environment variables for your Hive account.  This will take many minutes:

```shell
pytest --runslow
```

### Building the image locally with Docker

Locally build the podping-hivewriter container with a "develop" tag

```shell
docker build -t podping-hivewriter:develop .
```

See above for more details on running the docker CLI.

## Hive account

If you need a Hive account, please download the [Hive Keychain extension for your browser](https://hive-keychain.com/) then use this link to get your account from [https://HiveOnboard.com?ref=podping](https://hiveonboard.com?ref=podping). You will need at least 20 Hive Power "powered up" to get started (worth around $10). Please contact [@brianoflondon](https://peakd.com/@brianoflondon) brian@podping.org if you need assistance getting set up.

If you use the [Hiveonboard]((https://hiveonboard.com?ref=podping)) link `podping` will **delegate** enough Hive Power to get you started. If, for any reason, Hiveonboard is not giving out free accounts, please contact [@brianoflondon](https://peakd.com/@brianoflondon) either on [PodcastIndex Social](https://podcastindex.social/invite/U2m6FY3T) or [Telegram](https://t.me/brianoflondon).

### Permissions and Authorization

You don't need permission, but you do need to tell `podping` that you want to send valid `podpings`:

- Hive is a so-called "permissionless" blockchain.  Once you have a Hive Account and a minimal amount of Hive Power, that account can post to Hive, including sending `podpings`.
- Nobody can block any valid Hive Account from sending and nobody can help you if you lose your keys.
- Whilst anyone can post `podpings` to Hive, there is a need to register your Hive Accountname for those `podpings` to be recognized by all clients.  This is merely a spam-prevention measure and clients may choose to ignore it.
- Please contact new@podping.org or send a Hive Transfer to [@podping](https://peakd.com/@podping) to have your account validated.
- Side note on keys: `podping` uses the `posting-key` which is the lowest value of the four Hive keys (`owner`, `active`, `memo`, `posting` and there is usually a `master password` which can generate all the keys). That is not to say that losing control of it is a good idea, but that key is not authorized to make financially important transfers. It can, however, post public information so should be treated carefully and kept secure.

For a [comprehensive explanation of Hive and Podping, please see this post](https://peakd.com/podping/@brianoflondon/podping-and-podcasting-20-funding-to-put-hive-at-the-center-of-global-podcasting-infrastructure).