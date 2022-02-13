# `podping`

**Usage**:

```console
$ podping [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--medium TEXT`: The medium of the feed being updated. If used in combination with the 'server', this sets the default medium only. Must be one of the following: blog music audiobook newsletter video film podcast  [env var: PODPING_MEDIUM; default: podcast]
* `--reason TEXT`: The reason the feed is being updated. If used in combination with the 'server', this sets the default reason only. Must be one of the following: update live liveEnd  [env var: PODPING_REASON; default: update]
* `--hive-account TEXT`: Hive account used to post  [env var: PODPING_HIVE_ACCOUNT, HIVE_ACCOUNT, HIVE_SERVER_ACCOUNT; required]
* `--hive-posting-key TEXT`: Hive account used to post  [env var: PODPING_HIVE_POSTING_KEY, HIVE_POSTING_KEY; required]
* `--sanity-check / --no-sanity-check`: By default, podping will test for available resources and the ability to post to the Hive chain on the given hive account at startup by posting startup information. Disabling this will result in a faster startup, time, but may result in unexpected errors.  [env var: PODPING_SANITY_CHECK; default: True]
* `--livetest / --no-livetest`: Use live Hive chain but write with id=podping-livetest. Enable this if you want to validate posting to Hive without notifying podping watchers. Used internally for end-to-end tests.  [env var: PODPING_LIVETEST; default: False]
* `--dry-run / --no-dry-run`: Run through all posting logic without posting to the chain.  [env var: PODPING_DRY_RUN; default: False]
* `--status / --no-status`: Periodically prints a status message. Runs every diagnostic_report_period defined in podping_settings  [env var: PODPING_STATUS; default: True]
* `--ignore-config-updates / --no-ignore-config-updates`: By default, podping will periodically pull new settings from the configured Hive control account, allowing real time updates to adapt to changes in the Hive network. This lets you ignore these updates if needed.  [env var: PODPING_IGNORE_CONFIG_UPDATES; default: False]
* `--i-know-what-im-doing`: Set this if you really want to listen on all interfaces.  [env var: PODPING_I_KNOW_WHAT_IM_DOING; default: False]
* `--debug / --no-debug`: Print debug log messages  [env var: PODPING_DEBUG; default: False]
* `--version`
* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `server`: Run a Podping server.
* `write`: Write one or more IRIs to the Hive blockchain...

## `podping server`

Run a Podping server.  Listens for IRIs on the given address/port with ZeroMQ and
submits them to the Hive blockchain in batches.

Example with default localhost:9999 settings:
```
podping --hive-account <your-hive-account> --hive-posting-key <your-posting-key> server

2022-01-17T13:16:43+0200 | INFO | podping 1.1.0a1 starting up in server mode
2022-01-17T13:16:44+0200 | INFO | Podping startup sequence initiated, please stand by, full bozo checks in operation...
2022-01-17T13:16:45+0200 | INFO | Testing Account Resource Credits - before 99.73%
2022-01-17T13:16:48+0200 | INFO | Calculating Account Resource Credits for 100 pings: 8.55% | Capacity: 1,169
2022-01-17T13:16:49+0200 | INFO | Configuration override from Podping Hive: hive_operation_period=30 max_url_list_bytes=8000 diagnostic_report_period=180 control_account='podping' control_account_check_period=180 test_nodes=('https://testnet.openhive.network',)
2022-01-17T13:16:51+0200 | INFO | Lighthive Node: https://api.hive.blog
2022-01-17T13:16:51+0200 | INFO | JSON size: 179
2022-01-17T13:16:51+0200 | INFO | Startup of Podping status: SUCCESS! Hit the BOOST Button.
2022-01-17T13:16:53+0200 | INFO | Lighthive Fastest: https://api.deathwing.me
2022-01-17T13:16:53+0200 | INFO | Hive account: @podping.bol
2022-01-17T13:16:53+0200 | INFO | Running ZeroMQ server on 127.0.0.1:9999
2022-01-17T13:16:54+0200 | INFO | Lighthive Fastest: https://api.deathwing.me
2022-01-17T13:16:54+0200 | INFO | Status - Uptime: 0:00:10 | IRIs Received: 0 | IRIs Deduped: 0 | IRIs Sent: 0 | last_node: https://api.deathwing.me
```

**Usage**:

```console
$ podping server [OPTIONS] [LISTEN_IP] [LISTEN_PORT]
```

**Arguments**:

* `[LISTEN_IP]`: IP to listen on. Should accept any ZeroMQ-compatible host string. WARNING: DO NOT run this on a publicly accessible host. There currently is NO authentication required to submit to the server. Set to * or 0.0.0.0 for all interfaces. IPv6 not currently supported.  [env var: PODPING_LISTEN_IP;default: 127.0.0.1]
* `[LISTEN_PORT]`: Port to listen on.  [env var: PODPING_LISTEN_PORT;default: 9999]

**Options**:

* `--help`: Show this message and exit.

## `podping write`

Write one or more IRIs to the Hive blockchain without running a server.


Example writing three IRIs:
```
podping --hive-account <your-hive-account> --hive-posting-key <your-posting-key> --no-sanity-check write https://www.example.com/feed.xml https://www.example.com/pódcast.xml ipns://example.com/feed.xml

2021-08-30T00:14:35-0500 | INFO | Hive account: @podping.test
2021-08-30T00:14:35-0500 | INFO | Received 3 IRIs
2021-08-30T00:14:37-0500 | INFO | Transaction sent: c9cbaace76ec365052c11ec4a3726e4ed3a7c54d - JSON size: 170
```

Adding a Medium and Reason:
```
podping --hive-account <your-hive-account> --hive-posting-key <your-posting-key> --no-dry-run --no-sanity-check write https://3speak.tv/rss/podping.xml --medium video --reason update
```


Or add `--dry-run` to test functionality without broadcasting:
```
podping --hive-account <your-hive-account> --hive-posting-key <your-posting-key> --dry-run --no-sanity-check write https://www.example.com/feed.xml

2021-08-30T00:15:59-0500 | INFO | Hive account: @podping.test
2021-08-30T00:15:59-0500 | INFO | Received 1 IRIs
2021-08-30T00:16:00-0500 | INFO | Not broadcasting anything!
2021-08-30T00:16:01-0500 | INFO | Transaction sent: 00eae43df4a202d94ef6cb797c05f39fbb50631b - JSON size: 97
```

**Usage**:

```console
$ podping write [OPTIONS] IRI...
```

**Arguments**:

* `IRI...`: One or more whitepace-separated IRIs to post to Hive. This will fail if you try to send too many at once.  [env var: PODPING_IRI;required]

**Options**:

* `--help`: Show this message and exit.
