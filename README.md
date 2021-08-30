# podping-hivewriter
The Hive writer component of podping.

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

After that you should be able to run the `podping` command or run the tests:

```shell
pytest
```

To run all tests, make sure to set the necessary environment variables for your Hive account.  This can take many minutes:

```shell
pytest --runslow
```
