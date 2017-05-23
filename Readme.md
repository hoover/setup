Scripts to install and configure [Hoover](https://hoover.github.io)

### Getting started
This magic script will create a folder (named `hoover` by default) and install
components in it:

* Clones of the `search`, `snoop` and `ui` repos
* Virtualenvs and Python dependencies for `search` and `snoop`
* npm dependencies for `ui`

```shell
python3.5 <(curl -sL https://github.com/hoover/setup/raw/master/install.py)
```

To run the servers, start these two daemons from a daemon manager like
supervisor:

```shell
bin/hoover webserver snoop --host=localhost --port=9000
bin/hoover webserver search --host=localhost --port=8000
```

Later, if you want to upgrade to the latest version:

```shell
bin/hoover update
bin/hoover upgrade
```

### Environment variables

The following environment variables are used to specify different arguments for the setup:

| Name                           | Explanation                                                         | Default            |
|--------------------------------|---------------------------------------------------------------------|--------------------|
| `HOOVER_HOME`                  | The path where Hoover is installed.                                 | `pwd() / hoover`   |
| `HOOVER_VIRTUALENV_URL`        | The source of the virtualenv package.                               |                    |
| `HOOVER_SETUPTOOLS_URL`        | The source of the setuptools package.                               |                    |
| `HOOVER_PIP_URL`               | The source of the pip package.                                      |                    |
| `HOOVER_SEARCH_DB`             | The postgres database that `search` uses.                           | `hoover-search`    |
| `HOOVER_SNOOP_DB`              | The postgresql database that `snoop` uses.                          | `hoover-snoop`     |
| `HOOVER_ES_URL`                | The elasticsearch URL that will be used.                            | `localhost:9200`   |
| `HOOVER_TIKA_URL`              | The Apache Tika URL that will be used by `snoop`. Optional.         | `None`             |
| `HOOVER_SNOOP_SEVENZIP_EXEC`   | The `7z` executable that will be used by `snoop`. Optional.         | `which 7z`         |
| `HOOVER_SNOOP_MSGCONVERT_EXEC` | The `msgconvert` executable that will be used by `snoop`. Optional. | `which msgconvert` |
| `HOOVER_SNOOP_READPST_EXEC`    | The `readpst` executable that will be used by `snoop`. Optional.    | `which readpst`    |
| `HOOVER_SNOOP_GPG_EXEC`        | The `gpg` executable that will be used by `snoop`. Optional.        | `which gpg`        |
| `HOOVER_SETUP_REPO`            | The git repo from where the `setup` repo is cloned.                 |                    |
| `HOOVER_SETUP_BRANCH`          | The branch / version that is checked out for the `setup` repo.      | `master`           |
| `HOOVER_SEARCH_REPO`           | The git repo from where the `search` repo is cloned.                |                    |
| `HOOVER_SNOOP_REPO`            | The git repo from where the `snoop` repo is cloned.                 |                    |
| `HOOVER_UI_REPO`               | The git repo from where the `ui` repo is cloned.                    |                    |
| `HOOVER_BOOTSTRAP_NO_DB`       | Don't assume the databases exist on bootstrap. Run `upgrade` when they're available. | `None`             |
| `HOOVER_OAUTH_LIQUID_URL`      | The URL of the [liquid-core](https://github.com/liquidinvestigations/core) OAuth2 provider.||
| `HOOVER_OAUTH_CLIENT_ID`       | The client ID to be used with the [liquid-core](https://github.com/liquidinvestigations/core) OAuth2 provider.||
| `HOOVER_OAUTH_CLIENT_SECRET`   | The client secret to be used with the [liquid-core](https://github.com/liquidinvestigations/core) OAuth2 provider.||
| `HOOVER_CONFIG_DIR`            | The directory in which the config files are saved. Symlinks are made to the actual files.||

