# `podping`

**Usage**:

```console
$ podping [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--hive-account TEXT`: Hive account used to post  [env var: PODPING_HIVE_ACCOUNT, HIVE_ACCOUNT, HIVE_SERVER_ACCOUNT; required]
* `--hive-posting-key TEXT`: Hive account used to post  [env var: PODPING_HIVE_POSTING_KEY, HIVE_POSTING_KEY; required]
* `--sanity-check / --no-sanity-check`: By default, podping will test for available resources and the ability to post to the Hive chain on the given hive account at startup by posting startup information. Disabling this will result in a faster startup, time, but may result in unexpected errors.  [env var: PODPING_SANITY_CHECK; default: True]
* `--livetest / --no-livetest`: Use live Hive chain but write with id=podping-livetest. Enable this if you want to validate posting to Hive without notifying podping watchers. Used internally for end-to-end tests.  [env var: PODPING_LIVETEST; default: False]
* `--dry-run / --no-dry-run`: Run through all posting logic without posting to the chain.  [env var: PODPING_DRY_RUN; default: False]
* `--ignore-config-updates / --no-ignore-config-updates`: By default, podping will periodically pull new settings from the configured Hive control account, allowing real time updates to adapt to changes in the Hive network. This lets you ignore these updates if needed.  [env var: PODPING_IGNORE_CONFIG_UPDATES; default: False]
* `--debug / --no-debug`: Print debug log messages  [env var: PODPING_DEBUG; default: False]
* `--version`
* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `server`
* `write`

## `podping server`

**Usage**:

```console
$ podping server [OPTIONS] [LISTEN_IP] [LISTEN_PORT]
```

**Arguments**:

* `[LISTEN_IP]`: IP to listen on. Should accept any ZeroMQ-compatible host string. WARNING: DO NOT run this on a publicly accessible host. There currently is NO authentication required to submit to the server. Set to * or 0.0.0.0 for all interfaces. IPv6 not currently supported.  [env var: PODPING_LISTEN_IP;default: localhost]
* `[LISTEN_PORT]`: Port to listen on.  [env var: PODPING_LISTEN_PORT;default: 9999]

**Options**:

* `--status / --no-status`: Periodically prints a status message. Runs every diagnostic_report_period defined in podping_settings  [default: True]
* `--i-know-what-im-doing`: Set this if you really want to listen on all interfaces.  [default: False]
* `--help`: Show this message and exit.

## `podping write`

**Usage**:

```console
$ podping write [OPTIONS] IRI...
```

**Arguments**:

* `IRI...`: One or more whitepace-separated IRIs to post to Hive. This will fail if you try to send too many at once.  [env var: PODPING_IRI;required]

**Options**:

* `--help`: Show this message and exit.
