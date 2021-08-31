# podping-hivewriter
The Hive writer component of podping. You will need a Hive account, see section [Hive account and Authorization](#hive-account) below.

## Linux CLI Install

### Using [pipx](https://pypa.github.io/pipx/) (preferred over pip)
```shell
pipx install podping-hivewriter
```

### Using pip
```shell
pip install --user podping-hivewriter
```

Make sure you have `~/.local/bin/` on your `PATH`.

See the dedicated [CLI docs](cli.md) for more information.

## Container

## docker-compose

TODO

### Building the image with Docker

Locally build the podping-hivewriter container with a "develop" tag

```shell
docker build -t podpinghivewriter:develop .
```


### Running the image

Run the locally built image in a container, passing local port 9999 to port 9999 in the container.
ENV variables can be passed to docker with `--env-file` option after modifying the `.env.EXAMPLE` file and renaming it to `.env`

```shell
docker run --rm -p 9999:9999 --env-file .env --name podping podpinghivewriter:develop
```

Running with command line options, like `--dry-run` for example, add them with the full podping command.
Settings can also be passed with the `-e` option for Docker.  Note, we leave out `-p 9999:9999` here because we're not running the server.

```shell
docker run --rm \
    -e PODPING_HIVE_ACCOUNT=<account> \
    -e PODPING_HIVE_POSTING_KEY=<posting-key> \
    podpinghivewriter:develop \
    podping --dry-run write https://www.example.com/feed.xml
```

As another example for running a server, to run in *detached* mode, note the `-d` in the `docker run` options. Also note that `client` or `server` must come *after* the command line options for `podping`:
```shell
docker run --rm -d \
    -p 9999:9999 --env-file .env \
    --name podping podpinghivewriter:develop \
    podping --livetest server
```

One running you can view and follow the live output with:
```shell
docker logs podping -f
```

See the [CLI docs](cli.md) for default values.

## Development

We use [poetry](https://python-poetry.org/) for dependency management.  Once you have it, clone this repo and run:

```shell
poetry install
```

Then to switch to the virtual environment, use:

```shell
poetry shell
```
Make sure you have a `.env` file with a valid `PODPING_HIVE_ACCOUNT` and `PODPING_HIVE_POSTING_KEY` set.

After that you should be able to run the `podping` command or run the tests:

```shell
pytest
```

To run all tests, make sure to set the necessary environment variables for your Hive account.  This can take many minutes:

```shell
pytest --runslow
```

## Hive account

If you need a Hive account, please download the [Hive Keychain extension for your browser](https://hive-keychain.com/) then use this link to get your account from [https://HiveOnboard.com?ref=podping](https://hiveonboard.com?ref=podping). You will need at least 20 Hive Power "powered up" to get started (worth around $10). Please contact @brianoflondon brian@podping.org if you need assistance getting set up.

If you use the [Hiveonboard]((https://hiveonboard.com?ref=podping)) link `podping` will **delegate** enough Hive Power to get you started.

### Permissions and Authorization

You don't need permission, but you do need to tell `podping` that you want to send valid `podpings`:

- Hive is a so-called "permissionless" blockchain. Once you have a Hive Account and a minimal amount of Hive Power, that account can post to Hive, including sending `podpings`;

- Nobody can block any valid Hive Account from sending and nobody can help you if you lose your keys;

- Whilst anyone can post `podpings` to Hive, there is a need to register your Hive Accountname for those `podpings` to be recognized by all clients;

- Please contact new@podping.org or send a Hive Transfer to [@podping](https://peakd.com/@podping) to have your account validated.

For a [comprehensive explanation of Hive and Podping, please see this post](https://peakd.com/podping/@brianoflondon/podping-and-podcasting-20-funding-to-put-hive-at-the-center-of-global-podcasting-infrastructure).