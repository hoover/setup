import sys
import os
import random
import math
import subprocess
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import contextmanager
from textwrap import dedent
from urllib.request import urlretrieve
from parser import HooverParser

DEFAULT_VIRTUALENV_URL = 'https://github.com/pypa/virtualenv/raw/master/virtualenv.py'
DEFAULT_SETUPTOOLS_URL = 'https://pypi.python.org/packages/8a/1f/e2e14f0b98d0b6de6c3fb4e8a3b45d3b8907783937c497cb53539c0d2b19/setuptools-28.6.1-py2.py3-none-any.whl'
DEFAULT_PIP_URL = 'https://pypi.python.org/packages/9c/32/004ce0852e0a127f07f358b715015763273799bd798956fa930814b60f39/pip-8.1.2-py2.py3-none-any.whl'
DEFAULT_SEARCH_REPO = 'https://github.com/hoover/search.git'
DEFAULT_SNOOP_REPO = 'https://github.com/hoover/snoop.git'
DEFAULT_UI_REPO = 'https://github.com/hoover/ui.git'

HOOVER_SCRIPT = """\
#!/bin/sh
cd '{setup}'
export HOOVER_HOME='{home}'
exec {python} hoover_script.py "$@"
"""

_home = os.environ.get('HOOVER_HOME')
if not _home:
    raise RuntimeError("HOOVER_HOME environment variable is not set")
home = Path(_home)

interactive_mode = False

def question(label, default):
    rv = input("{} [{}]: ".format(label, default))
    return rv.strip() or default

class Param:
    def __init(self, name, default, environ=None, question_label=None):
        self.name = name
        self.default = default
        self.environ = environ
        self.question_label = question_label
        self.value = None

    def get(self):
        if self.value is not None:
            return self.value

        if os.getenv(self.environ):
            self.value = os.getenv(self.environ)
        elif interactive_mode and question_label is not None:
            self.value = question(self.question_label, self.default)
        else:
            self.value = self.default

        if self.value is None:
            raise RuntimeError(("The {} param was not set! Use the {} " +
                "environment variable to set it.").format(self.name, self.environ))

        return self.value

    def get_path(self):
        return Path(self.get())

VIRTUALENV_URL = Param('virtualenv_url', DEFAULT_VIRTUALENV_URL ,'HOOVER_VIRTUALENV_URL');
SETUPTOOLS_URL = Param('setuptools_url', DEFAULT_SETUPTOOLS_URL ,'HOOVER_SETUPTOOLS_URL');
PIP_URL        = Param('pip_url',        DEFAULT_PIP_URL        ,'HOOVER_PIP_URL');
SEARCH_REPO    = Param('search_repo',    DEFAULT_SEARCH_REPO    ,'HOOVER_SEARCH_REPO');
SNOOP_REPO     = Param('snoop_repo',     DEFAULT_SNOOP_REPO     ,'HOOVER_SNOOP_REPO');
UI_REPO        = Param('ui_repo',        DEFAULT_UI_REPO        ,'HOOVER_UI_REPO');

def runcmd(cmd, **kwargs):
    if 'env' not in kwargs:
        kwargs['env'] = dict(os.environ)
        kwargs['env'].pop('__PYVENV_LAUNCHER__', None)
    subprocess.check_call([str(c) for c in cmd], **kwargs)

@contextmanager
def tmp_virtualenv():
    with TemporaryDirectory() as _tmp:
        def download(url, directory):
            name = url.split('/')[-1]
            urlretrieve(url, str(directory / name))

        def run(target):
            runcmd([
                sys.executable,
                tmp / 'virtualenv.py',
                '--extra-search-dir={}'.format(tmp),
                target,
            ])
            runcmd([
                target / 'bin' / 'pip',
                'install', '-U', 'setuptools', 'pip',
            ])

        tmp = Path(_tmp)
        download(VIRTUALENV_URL.get(), tmp)
        download(SETUPTOOLS_URL.get(), tmp)
        download(PIP_URL.get(), tmp)
        yield run

def git_clone(url, directory):
    runcmd(['git', 'clone', url], cwd=str(directory))

def preflight():
    manage_py('search', 'migrate')
    manage_py('snoop', 'migrate')
    manage_py('search', 'downloadassets')
    manage_py('search', 'collectstatic', '--noinput')
    runcmd(['npm', 'install'], cwd=str(home / 'ui'))
    runcmd(['./run', 'build'], cwd=str(home / 'ui'))

def create_scripts():
    (home / 'bin').mkdir(exist_ok=True)
    bin_hoover = home / 'bin' / 'hoover'
    with bin_hoover.open('w', encoding='utf-8') as f:
        f.write(HOOVER_SCRIPT.format(
            python=sys.executable,
            home=home,
            setup=home / 'setup',
        ))
    bin_hoover.chmod(0o755)

def create_cache_dir():
    cache = home / 'cache'
    cache.mkdir()
    for directory in ['msg', 'archives', 'pst', 'gpg_home']:
        (cache / directory).mkdir()

def bootstrap(args):
    git_clone(SEARCH_REPO.get(), home)
    git_clone(SNOOP_REPO.get(), home)
    git_clone(UI_REPO.get(), home)

    with tmp_virtualenv() as create_virtualenv:
        create_virtualenv(home / 'venvs' / 'search')
        create_virtualenv(home / 'venvs' / 'snoop')

    venv = lambda name, cmd: home / 'venvs' / name / 'bin' / cmd
    runcmd([
        venv('search', 'pip'), 'install',
        '-r', home / 'search' / 'requirements.txt',
    ])
    runcmd([
        venv('snoop', 'pip'), 'install',
        '-r', home / 'snoop' / 'requirements.txt',
    ])
    create_cache_dir()
    create_scripts()
    configure([])
    preflight()

def random_secret_key(entropy=256):
    vocabulary = ('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        '0123456789!@#$%^&*()-=+[]{}:.<>/?')
    entropy_per_char = math.log(len(vocabulary), 2)
    chars = int(math.ceil(entropy / entropy_per_char))
    urandom = random.SystemRandom()
    return ''.join(urandom.choice(vocabulary) for _ in range(chars))

def configure_search():
    local_py = home / 'search' / 'hoover' / 'site' / 'settings' / 'local.py'
    if local_py.exists():
        print("{!s} already exists, skipping".format(local_py))
        return

    print("Configuration values for hoover-search")
    values = {
        'ui_root': str(home / 'ui' / 'build'),
        'secret_key': random_secret_key(),
        'db_name': question("PostgreSQL search database", 'hoover-search'),
        'es_url': question("Elasticsearch URL", 'http://localhost:9200'),
    }
    template = dedent("""\
        from pathlib import Path
        base_dir = Path(__file__).absolute().parent.parent.parent.parent
        SECRET_KEY = {secret_key!r}
        DATABASES = {{
            'default': {{
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'NAME': {db_name!r},
            }},
        }}
        STATIC_ROOT = str(base_dir / 'static')
        HOOVER_UPLOADS_ROOT = str(base_dir / 'uploads')
        HOOVER_ELASTICSEARCH_URL = {es_url!r}
        HOOVER_UI_ROOT = {ui_root!r}
    """)
    with local_py.open('w', encoding='utf-8') as f:
        f.write(template.format(**values))

def configure_snoop():
    local_py = home / 'snoop' / 'snoop' / 'site' / 'settings' / 'local.py'
    if local_py.exists():
        print("{!s} already exists, skipping".format(local_py))
        return

    print("Configuration values for hoover-snoop")
    values = {
        'secret_key': random_secret_key(),
        'db_name': question("PostgreSQL snoop database", 'hoover-snoop'),
        'es_url': question("Elasticsearch URL", 'http://localhost:9200'),
        'tika_url': question("Tika URL", None),
        '7z_exec': question("Path to 7z executable", shutil.which('7z')),
        '7z_cache': str(home / 'cache' / 'archives'),
        'msgconvert_exec': question("Path to msgconvert executable", shutil.which('msgconvert')),
        'msg_cache': str(home / 'cache' / 'msg'),
        'readpst_exec': question("Path to readpst executable", shutil.which('readpst')),
        'pst_cache': str(home / 'cache' / 'pst'),
        'gpg_exec': question("Path to gpg executable", shutil.which('gpg')),
        'gpg_home': str(home / 'cache' / 'gpg_home'),
    }
    template = dedent("""\
        SECRET_KEY = {secret_key!r}
        DATABASES = {{
            'default': {{
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'NAME': {db_name!r},
            }}
        }}

        SNOOP_ELASTICSEARCH_URL = {es_url!r}
        SNOOP_TIKA_SERVER_ENDPOINT = {tika_url!r}

        SNOOP_ARCHIVE_CACHE_ROOT = {7z_cache!r}
        SNOOP_SEVENZIP_BINARY = {7z_exec!r}

        SNOOP_MSG_CACHE = {msg_cache!r}
        SNOOP_MSGCONVERT_SCRIPT = {msgconvert_exec!r}

        SNOOP_PST_CACHE_ROOT = {pst_cache!r}
        SNOOP_READPST_BINARY = {readpst_exec!r}

        SNOOP_GPG_HOME = {gpg_home!r}
        SNOOP_GPG_BINARY = {gpg_exec!r}
    """)
    with local_py.open('w', encoding='utf-8') as f:
        f.write(template.format(**values))

def configure(args):
    configure_search()
    configure_snoop()

def update(args):
    runcmd(['git', 'pull'], cwd=str(home / 'setup'))
    create_scripts()

def manage_py(name, *args):
    python = home / 'venvs' / name / 'bin' / 'python'
    runcmd([python, home / name / 'manage.py'] + list(args))

def upgrade(args):
    runcmd(['git', 'pull'], cwd=str(home / 'search'))
    runcmd(['git', 'pull'], cwd=str(home / 'snoop'))
    runcmd(['git', 'pull'], cwd=str(home / 'ui'))
    runcmd([home / 'venvs' / 'search' / 'bin' / 'pip-sync'],
        cwd=str(home / 'search'))
    runcmd([home / 'venvs' / 'snoop' / 'bin' / 'pip-sync'],
        cwd=str(home / 'snoop'))
    preflight()

def execv(args):
    os.execv(args[0], args)

def webserver(args):
    parser = HooverParser(description="Run webserver")
    parser.add_argument('server', choices=['search', 'snoop'])
    (options, extra_args) = parser.parse_known_args(args)

    if options.server == 'search':
        waitress = str(home / 'venvs' / 'search' / 'bin' / 'waitress-serve')
        os.chdir(str(home / 'search'))
        execv([waitress] + extra_args + ['hoover.site.wsgi:application'])

    if options.server == 'snoop':
        waitress = str(home / 'venvs' / 'snoop' / 'bin' / 'waitress-serve')
        os.chdir(str(home / 'snoop'))
        execv([waitress] + extra_args + ['snoop.site.wsgi:application'])

def snoop(args):
    py = str(home / 'venvs' / 'snoop' / 'bin' / 'python')
    manage_py = str(home / 'snoop' / 'manage.py')
    execv([py, manage_py] + args)

def search(args):
    py = str(home / 'venvs' / 'search' / 'bin' / 'python')
    manage_py = str(home / 'search' / 'manage.py')
    execv([py, manage_py] + args)

def main():
    parser = HooverParser(description="Hoover setup")
    parser.add_subcommands('cmd', [
        bootstrap, configure, update, upgrade,
        webserver, snoop, search,
    ])
    (options, extra_args) = parser.parse_known_args()
    options.cmd(extra_args)

if __name__ == '__main__':
    main()
