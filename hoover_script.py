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

param_list = []

class Param:
    def __init__(self, name, default, environ=None, question_label=None, required=True):
        self.name = name
        self.default = default
        self.environ = environ
        self.question_label = question_label
        self.required = required
        self.value = None
        param_list.append(self)

    @staticmethod
    def _question(label, default):
        rv = input("{} [{}]: ".format(label, default))
        return rv.strip() or default

    def get(self):
        if self.value is not None:
            return self.value

        if os.getenv(self.environ):
            self.value = os.getenv(self.environ)
        elif interactive_mode and self.required and self.question_label is not None:
            self.value = self._question(self.question_label, self.default)
        else:
            self.value = self.default

        if self.value is None and self.required:
            raise RuntimeError(("The {} param was not set! Use the {} " +
                "environment variable to set it.").format(self.name, self.environ))

        return self.value

    def get_path(self):
        return Path(self.get())

class Params:
    virtualenv_url = Param(
        name = 'virtualenv_url',
        default = 'https://github.com/pypa/virtualenv/raw/master/virtualenv.py',
        environ = 'HOOVER_VIRTUALENV_URL'
    )

    setuptools_url = Param(
        name = 'setuptools_url',
        default = 'https://pypi.python.org/packages/8a/1f/e2e14f0b98d0b6de6c3fb4e8a3b45d3b8907783937c497cb53539c0d2b19/setuptools-28.6.1-py2.py3-none-any.whl',
        environ = 'HOOVER_SETUPTOOLS_URL'
    )

    pip_url = Param(
        name = 'pip_url',
        default = 'https://pypi.python.org/packages/9c/32/004ce0852e0a127f07f358b715015763273799bd798956fa930814b60f39/pip-8.1.2-py2.py3-none-any.whl',
        environ = 'HOOVER_PIP_URL'
    )

    search_repo = Param(
        name = 'search_repo',
        default = 'https://github.com/hoover/search.git',
        environ = 'HOOVER_SEARCH_REPO'
    )

    bootstrap_no_db = Param(
        name = 'bootstrap_no_db',
        default = False,
        environ = 'HOOVER_BOOTSTRAP_NO_DB',
        required = False
    )

    snoop_repo = Param(
        name = 'snoop_repo',
        default = 'https://github.com/hoover/snoop.git',
        environ = 'HOOVER_SNOOP_REPO'
    )

    ui_repo = Param(
        name = 'ui_repo',
        default = 'https://github.com/hoover/ui.git',
        environ = 'HOOVER_UI_REPO'
    )

    search_db = Param(
        name = 'search_db',
        default = 'hoover-search',
        environ = 'HOOVER_SEARCH_DB',
        question_label = "PostgreSQL search database"
    )

    snoop_db = Param(
        name = 'snoop_db',
        default = 'hoover-snoop',
        environ = 'HOOVER_SNOOP_DB',
        question_label = "PostgreSQL snoop database"
    )

    es_url = Param(
        name = 'es_url',
        default = 'http://localhost:9200',
        environ = 'HOOVER_ES_URL',
        question_label = "Elasticsearch URL"
    )

    tika_url = Param(
        name = 'tika_url',
        default = None,
        environ = 'HOOVER_TIKA_URL',
        question_label = "Tika URL",
        required = False
    )

    sevenzip_exec = Param(
        name = '7z_exec',
        default = shutil.which('7z'),
        environ = 'HOOVER_SNOOP_SEVENZIP_EXEC',
        question_label = "Path to 7z executable",
        required = False
    )

    msgconvert_exec = Param(
        name = 'msgconvert_exec',
        default = shutil.which('msgconvert'),
        environ = 'HOOVER_SNOOP_MSGCONVERT_EXEC',
        question_label = "Path to msgconvert executable",
        required = False
    )

    readpst_exec = Param(
        name = 'readpst_exec',
        default = shutil.which('readpst'),
        environ = 'HOOVER_SNOOP_READPST_EXEC',
        question_label = "Path to readpst executable",
        required = False
    )

    gpg_exec = Param(
        name = 'gpg_exec',
        default = shutil.which('gpg'),
        environ = 'HOOVER_SNOOP_GPG_EXEC',
        question_label = "Path to gpg executable",
        required = False
    )

    allowed_hosts = Param(
        name = 'allowed_hosts',
        default = 'localhost',
        environ = 'HOOVER_ALLOWED_HOSTS',
        question_label = "Space separated list with the allowed hosts"
    )

    oauth_client_id = Param(
        name = 'oauth_client_id',
        default = None,
        environ = 'HOOVER_OAUTH_CLIENT_ID',
        question_label = "Client ID for OAuth2",
        required = False
    )

    oauth_client_secret = Param(
        name = 'oauth_client_secret',
        default = None,
        environ = 'HOOVER_OAUTH_CLIENT_SECRET',
        question_label = "Client secret for OAuth2",
        required = False
    )

    oauth_liquid_url = Param(
        name = 'oauth_liquid_url',
        default = None,
        environ = 'HOOVER_OAUTH_LIQUID_URL',
        question_label = "URL that points to the liquid-core OAuth2 provider",
        required = False
    )

    config_dir = Param(
        name = 'config_dir',
        default = None,
        environ = 'HOOVER_CONFIG_DIR',
        question_label = "The directory in which the config files are saved. Symlinks are made to the actual files.",
        required = False
    )


for param in param_list:
    if param.required:
        param.get()

def list_params(args):
    print("Listing HOOVER SETUP params...")
    print()
    for param in Params.param_list:
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
        download(Params.virtualenv_url.get(), tmp)
        download(Params.setuptools_url.get(), tmp)
        download(Params.pip_url.get(), tmp)
        yield run

def git_clone(url, directory):
    runcmd(['git', 'clone', url], cwd=str(directory))

def migrate():
    manage_py('search', 'migrate')
    manage_py('snoop', 'migrate')

def preflight(run_migrations=True):
    if run_migrations:
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
    git_clone(Params.search_repo.get(), home)
    git_clone(Params.snoop_repo.get(), home)
    git_clone(Params.ui_repo.get(), home)

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
    configure_snoop(exist_ok=False)
    configure_search(exist_ok=False)
    preflight(not Params.bootstrap_no_db.get())

def random_secret_key(entropy=256):
    vocabulary = ('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        '0123456789!@#$%^&*()-=+[]{}:.<>/?')
    entropy_per_char = math.log(len(vocabulary), 2)
    chars = int(math.ceil(entropy / entropy_per_char))
    urandom = random.SystemRandom()
    return ''.join(urandom.choice(vocabulary) for _ in range(chars))

def configure_search(exist_ok = True):
    local_py = home / 'search' / 'hoover' / 'site' / 'settings' / 'local.py'
    if not exist_ok and local_py.exists():
        print("{!s} already exists, skipping".format(local_py))
        return

    if Params.config_dir.get() is not None:
        config_dir = Path(Params.config_dir.get())
        config_dir.mkdir(exist_ok=True, parents=True)
        (config_dir / 'search').mkdir(exist_ok=True)
        real_local_py = config_dir / 'search' / 'local.py'
        if not local_py.is_symlink() or not local_py.resolve().samefile(real_local_py):
            local_py.symlink_to(real_local_py)
        local_py = real_local_py

    print("Configuration values for hoover-search")
    values = {
        'ui_root': str(home / 'ui' / 'build'),
        'secret_key': random_secret_key(),
        'db_name': Params.search_db.get(),
        'es_url': Params.es_url.get(),
        'allowed_hosts': Params.allowed_hosts.get().split(),
        'oauth_client_id': Params.oauth_client_id.get(),
        'oauth_client_secret': Params.oauth_client_secret.get(),
        'oauth_liquid_url': Params.oauth_liquid_url.get(),
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

        HOOVER_OAUTH_LIQUID_URL = {oauth_liquid_url!r}
        HOOVER_OAUTH_LIQUID_CLIENT_ID = {oauth_client_id!r}
        HOOVER_OAUTH_LIQUID_CLIENT_SECRET = {oauth_client_secret!r}
    """)
    with local_py.open('w', encoding='utf-8') as f:
        f.write(template.format(**values))

def configure_snoop(exist_ok = True):
    local_py = home / 'snoop' / 'snoop' / 'site' / 'settings' / 'local.py'
    if not exist_ok and local_py.exists():
        print("{!s} already exists, skipping".format(local_py))
        return

    if Params.config_dir.get() is not None:
        config_dir = Path(Params.config_dir.get())
        config_dir.mkdir(exist_ok=True, parents=True)
        (config_dir / 'snoop').mkdir(exist_ok=True)
        real_local_py = config_dir / 'snoop' / 'local.py'
        if not local_py.is_symlink() or not local_py.resolve().samefile(real_local_py):
            local_py.symlink_to(real_local_py)
        local_py = real_local_py

    print("Configuration values for hoover-snoop")
    values = {
        'secret_key': random_secret_key(),
        'db_name':  Params.snoop_db.get(),
        'es_url':   Params.es_url.get(),
        'tika_url': Params.tika_url.get(),
        '7z_exec':  Params.sevenzip_exec.get(),
        '7z_cache': str(home / 'cache' / 'archives') if Params.sevenzip_exec.get() else None,
        'msgconvert_exec': Params.msgconvert_exec.get(),
        'msg_cache': str(home / 'cache' / 'msg') if Params.msgconvert_exec.get() else None,
        'readpst_exec': Params.readpst_exec.get(),
        'pst_cache': str(home / 'cache' / 'pst') if Params.readpst_exec.get() else None,
        'gpg_exec': Params.gpg_exec.get(),
        'gpg_home': str(home / 'cache' / 'gpg_home') if Params.gpg_exec.get() else None,
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

def reconfigure(args):
    configure_search(exist_ok=True)
    configure_snoop(exist_ok=True)

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
        bootstrap, reconfigure, update, upgrade,
        webserver, snoop, search, list_params,
    ])
    (options, extra_args) = parser.parse_known_args()
    options.cmd(extra_args)

if __name__ == '__main__':
    main()
