# podping-hivewriter
The hive writer component of podping.

## Building docker image

Locally build the podping-hivewriter container with a "develop" tag

`docker build -t podpinghivewriter:develop .`

TODO: Use Github CI/CD to do this automatically on commit and push to Docker Hub

## Running docker image

Run the locally built docker image in a container, passing local port 9999 to port 9999 in the container

`docker run --rm -p 9999:9999 -e HIVE_SERVER_ACCOUNT=<account> -e HIVE_POSTING_KEY=<posting-key> podpinghivewriter:develop`

Running with command line options, like testnet for example, add them at the end:

`docker run --rm -p 9999:9999 -e HIVE_SERVER_ACCOUNT=<account> -e HIVE_POSTING_KEY=<posting-key> podpinghivewriter:develop --test`

gpg test on umbrel pi