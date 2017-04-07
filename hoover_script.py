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

class Param:
    param_list = []

    def __init__(self, name, default, environ=None, question_label=None, optional=False):
        self.name = name
        self.default = default
        self.environ = environ
        self.question_label = question_label
        self.optional = optional
        self.value = None
        Param.param_list.append(self)

    @staticmethod
    def _question(label, default):
        rv = input("{} [{}]: ".format(label, default))
        return rv.strip() or default

    def get(self):
        if self.value is not None:
            return self.value

        if os.getenv(self.environ):
            self.value = os.getenv(self.environ)
        elif interactive_mode and question_label is not None:
            self.value = _question(self.question_label, self.default)
        else:
            self.value = self.default

        if self.value is None and not self.optional:
            raise RuntimeError(("The {} param was not set! Use the {} " +
                "environment variable to set it.").format(self.name, self.environ))

        return self.value

    def get_path(self):
        return Path(self.get())

VIRTUALENV_URL = Param(
        name = 'virtualenv_url',
        default = 'https://github.com/pypa/virtualenv/raw/master/virtualenv.py',
        environ = 'HOOVER_VIRTUALENV_URL'
)

SETUPTOOLS_URL = Param(
        name = 'setuptools_url',
        default = 'https://pypi.python.org/packages/8a/1f/e2e14f0b98d0b6de6c3fb4e8a3b45d3b8907783937c497cb53539c0d2b19/setuptools-28.6.1-py2.py3-none-any.whl',
        environ = 'HOOVER_SETUPTOOLS_URL'
)

PIP_URL = Param(
        name = 'pip_url',
        default = 'https://pypi.python.org/packages/9c/32/004ce0852e0a127f07f358b715015763273799bd798956fa930814b60f39/pip-8.1.2-py2.py3-none-any.whl',
        environ = 'HOOVER_PIP_URL'
)

SEARCH_REPO = Param(
        name = 'search_repo',
        default = 'https://github.com/hoover/search.git',
        environ = 'HOOVER_SEARCH_REPO'
)

BOOTSTRAP_NO_DB = Param(
        name = 'bootstrap_no_db',
        default = False,
        environ = 'HOOVER_BOOTSTRAP_NO_DB',
        optional = True
)

SNOOP_REPO = Param(
        name = 'snoop_repo',
        default = 'https://github.com/hoover/snoop.git',
        environ = 'HOOVER_SNOOP_REPO'
)

UI_REPO = Param(
        name = 'ui_repo',
        default = 'https://github.com/hoover/ui.git',
        environ = 'HOOVER_UI_REPO'
)

SEARCH_DB = Param(
        name = 'search_db',
        default = 'hoover-search',
        environ = 'HOOVER_SEARCH_DB',
        question_label = "PostgreSQL search database"
)

SNOOP_DB = Param(
        name = 'snoop_db',
        default = 'hoover-snoop',
        environ = 'HOOVER_SNOOP_DB',
        question_label = "PostgreSQL snoop database"
)

ES_URL = Param(
        name = 'es_url',
        default = 'http://localhost:9200',
        environ = 'HOOVER_ES_URL',
        question_label = "Elasticsearch URL"
)

TIKA_URL = Param(
        name = 'tika_url',
        default = None,
        environ = 'HOOVER_TIKA_URL',
        question_label = "Tika URL",
        optional = True
)

SEVENZIP_EXEC = Param(
        name = '7z_exec',
        default = shutil.which('7z'),
        environ = 'HOOVER_SNOOP_SEVENZIP_EXEC',
        question_label = "Path to 7z executable",
        optional = True
)

MSGCONVERT_EXEC = Param(
        name = 'msgconvert_exec',
        default = shutil.which('msgconvert'),
        environ = 'HOOVER_SNOOP_MSGCONVERT_EXEC',
        question_label = "Path to msgconvert executable",
        optional = True
)

READPST_EXEC = Param(
        name = 'readpst_exec',
        default = shutil.which('readpst'),
        environ = 'HOOVER_SNOOP_READPST_EXEC',
        question_label = "Path to readpst executable",
        optional = True
)

GPG_EXEC = Param(
        name = 'gpg_exec',
        default = shutil.which('gpg'),
        environ = 'HOOVER_SNOOP_GPG_EXEC',
        question_label = "Path to gpg executable",
        optional = True
)

ALLOWED_HOSTS = Param(
        name = 'allowed_hosts',
        default = 'localhost',
        environ = 'HOOVER_ALLOWED_HOSTS',
        question_label = "Space separated list with the allowed hosts"
)

def list_params(args):
    print("Listing HOOVER SETUP params...")
    print()
    for param in Param.param_list:
        print("====", param.name, "====")
        print("label:    ", param.question_label)
        print("env:      ", param.environ)
        print("default:  ", param.default)
        print("optional: ", param.optional)
        print("value:    ", param.get())
        print()

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

def migrate():
    manage_py('search', 'migrate')
    manage_py('snoop', 'migrate')

def preflight(skip_migrations=False):
    if not skip_migrations:
        migrate()
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
    preflight(BOOTSTRAP_NO_DB.get())

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
        'db_name': SEARCH_DB.get(),
        'es_url': ES_URL.get(),
        'allowed_hosts': ALLOWED_HOSTS.get().split(),
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

        ALLOWED_HOSTS = {allowed_hosts!r}

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
        'db_name':  SNOOP_DB.get(),
        'es_url':   ES_URL.get(),
        'tika_url': TIKA_URL.get(),
        '7z_exec':  SEVENZIP_EXEC.get(),
        '7z_cache': str(home / 'cache' / 'archives') if SEVENZIP_EXEC.get() else None,
        'msgconvert_exec': MSGCONVERT_EXEC.get(),
        'msg_cache': str(home / 'cache' / 'msg') if MSGCONVERT_EXEC.get() else None,
        'readpst_exec': READPST_EXEC.get(),
        'pst_cache': str(home / 'cache' / 'pst') if READPST_EXEC.get() else None,
        'gpg_exec': GPG_EXEC.get(),
        'gpg_home': str(home / 'cache' / 'gpg_home') if GPG_EXEC.get() else None,
    }
    template = dedent("""\
        SECRET_KEY = {secret_key!r}
        DATABASES = {{
            'default': {{
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'NAME': {db_name!r},
            }}
        }}

        ALLOWED_HOSTS = ["localhost"]

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
        webserver, snoop, search, list_params,
    ])
    (options, extra_args) = parser.parse_known_args()
    options.cmd(extra_args)

if __name__ == '__main__':
    main()
