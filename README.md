# podping-hivewriter
The hive writer component of podping.

These docs are in flux: a full docerhub image and a pypi version is being worked on. Right now, this libarary (from dev branches) can be experimented with by qualified individuals.

## Docker
### Building docker image

Locally build the podping-hivewriter container with a "develop" tag

`docker build -t podpinghivewriter:develop .`

TODO: Use Github CI/CD to do this automatically on commit and push to Docker Hub

### Running from docker image

Run the locally built docker image in a container, passing local port 9999 to port 9999 in the container.
ENV variables can be passed to Docker with `--env-file` option after modifying the `.env.EXAMPLE` file and renaming it to `.env`

`docker run --rm -p 9999:9999 --env-file .env --name podping_hivewriter podpinghivewriter:develop --bindall --zmq 9999`

Running with command line options, like testnet for example, add them at the end and enviornment settings can also be passed with the `-e` option for Docker:

`docker run --rm -p 9999:9999 -e HIVE_SERVER_ACCOUNT=<account> -e HIVE_POSTING_KEY=<posting-key> podpinghivewriter:develop --test --bindall`

By default `hive-writer` will run with the equivalent of `--zmq 9999` binding to `127.0.0.1` only. If you need to grant access from other IP addresses, pass the `--bindall` option. Within Docker you will need the `--bindall` option

## Python
### Poetry Install

If you want to run the Python scripts direct, after cloning the repository run:

`poetry install`

Then to switch to the virtual environment, use:

`poetry shell`

After that you should be able to run hive-writer with any of the command line options:

`python src/podping_hivewriter/hive_writer.py --help`


```
usage: hive-writer [options]

PodPing - Runs as a server and writes a stream of URLs to the Hive Blockchain
or sends a single URL to Hive (--url option) Defaults to running the --zmq
9999 and binding only to localhost

optional arguments:
  -h, --help      show this help message and exit
  -q, --quiet     Minimal output
  -v, --verbose   Lots of output
  -z , --zmq      <IP:port> for ZMQ to listen on for each new url, returns, if
                  IP is given, listens on that IP, otherwise only listens on
                  localhost
  -b, --bindall   If given, bind the ZMQ listening port to *, if not given
                  default binds ZMQ to localhost
  -u , --url      <url> Takes in a single URL and sends a single podping to
                  Hive, needs HIVE_SERVER_ACCOUNT and HIVE_POSTING_KEY ENV
                  variables set
  -t, --test      Use a test net API
  -e , --errors   Deliberately force error rate of <int>%
```