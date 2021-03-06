#!/bin/bash
set -x

export HOOVER_HOME=`mktemp -d`
export HOOVER_SETUP_BRANCH=master
export HOOVER_SEARCH_DB=hoover-temp-search
export HOOVER_SNOOP2_DB=hoover-temp-snoop2
export HOOVER_BOOTSTRAP_NO_DB=True
export HOOVER_ALLOWED_HOSTS="localhost https://hoover.example.org"
export HOOVER_CONFIG_DIR="$HOOVER_HOME/the/configuration/path"

#export HOOVER_VIRTUALENV_URL
#export HOOVER_SETUPTOOLS_URL
#export HOOVER_PIP_URL
#export HOOVER_ES_URL
#export HOOVER_SNOOP2_TIKA_URL
#export HOOVER_SETUP_REPO
#export HOOVER_SEARCH_REPO
#export HOOVER_SNOOP2_REPO
#export HOOVER_UI_REPO

python3 <(curl -sL https://raw.githubusercontent.com/hoover/setup/$HOOVER_SETUP_BRANCH/install.py)

createdb hoover-temp-search
createdb hoover-temp-snoop2

$HOOVER_HOME/bin/hoover upgrade
$HOOVER_HOME/bin/hoover search doctor
$HOOVER_HOME/bin/hoover snoop2 doctor

export HOOVER_OAUTH_CLIENT_ID=xxxx
export HOOVER_OAUTH_CLIENT_SECRET=xxxx
export HOOVER_OAUTH_LIQUID_URL=http://localhost

$HOOVER_HOME/bin/hoover reconfigure

(cd $HOOVER_HOME; PATH=$HOOVER_HOME/bin:$PATH PS1="ephemeral hoover $ " bash)

rm -rf $HOOVER_HOME

dropdb hoover-temp-search
dropdb hoover-temp-snoop2

