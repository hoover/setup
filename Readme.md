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
