import sys
import os
import random
import math
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import contextmanager
from textwrap import dedent
from urllib.request import urlretrieve

VIRTUALENV_URL = 'https://github.com/pypa/virtualenv/raw/master/virtualenv.py'
SETUPTOOLS_URL = 'https://pypi.python.org/packages/8a/1f/e2e14f0b98d0b6de6c3fb4e8a3b45d3b8907783937c497cb53539c0d2b19/setuptools-28.6.1-py2.py3-none-any.whl'
PIP_URL = 'https://pypi.python.org/packages/9c/32/004ce0852e0a127f07f358b715015763273799bd798956fa930814b60f39/pip-8.1.2-py2.py3-none-any.whl'
SEARCH_REPO = 'https://github.com/hoover/search.git'
SNOOP_REPO = 'https://github.com/hoover/snoop.git'
UI_REPO = 'https://github.com/hoover/ui.git'

HOOVER_SCRIPT = """\
#!/bin/sh
cd '{setup}'
export HOOVER_HOME='{home}'
{python} hoover_script.py "$@"
"""

_home = os.environ.get('HOOVER_HOME')
if not _home:
    raise RuntimeError("HOOVER_HOME environment variable is not set")
home = Path(_home)

def question(label, default):
    rv = input("{} [{}]: ".format(label, default))
    return rv.strip() or default

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
        download(VIRTUALENV_URL, tmp)
        download(SETUPTOOLS_URL, tmp)
        download(PIP_URL, tmp)
        yield run

def git_clone(url, directory):
    runcmd(['git', 'clone', url], cwd=str(directory))

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
        'db_name': question("PostgreSQL database", 'hoover-search'),
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
        'db_name': question("PostgreSQL database", 'hoover-snoop'),
        'es_url': question("Elasticsearch URL", 'http://localhost:9200'),
        'data_path': question("Path to dataset", '/tmp/dataset'),
    }
    template = dedent("""\
        SECRET_KEY = {secret_key!r}
        DATABASES = {{
            'default': {{
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'NAME': {db_name!r},
            }}
        }}
        SNOOP_ROOT = {data_path!r}
        SNOOP_ELASTICSEARCH_URL = {es_url!r}
    """)
    with local_py.open('w', encoding='utf-8') as f:
        f.write(template.format(**values))

def execv(args):
    os.execv(args[0], args)

def main(argv):
    if argv == ['bootstrap']:
        git_clone(SEARCH_REPO, home)
        git_clone(SNOOP_REPO, home)
        git_clone(UI_REPO, home)

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
        runcmd(['npm', 'install'], cwd=str(home / 'ui'))
        runcmd(['./run', 'build'], cwd=str(home / 'ui'))

        (home / 'bin').mkdir(exist_ok=True)
        bin_hoover = home / 'bin' / 'hoover'
        with bin_hoover.open('w', encoding='utf-8') as f:
            f.write(HOOVER_SCRIPT.format(
                python=sys.executable,
                home=home,
                setup=home / 'setup',
            ))
        bin_hoover.chmod(0o755)

        print("Success!")
        return

    if argv == ['configure']:
        configure_search()
        configure_snoop()
        return

    if argv[:1] == ['webserver']:
        if argv[1:2] == ['search']:
            waitress = str(home / 'venvs' / 'search' / 'bin' / 'waitress-serve')
            os.chdir(str(home / 'search'))
            execv([waitress] + argv[2:] + ['hoover.site.wsgi:application'])

        if argv[1:2] == ['snoop']:
            waitress = str(home / 'venvs' / 'snoop' / 'bin' / 'waitress-serve')
            os.chdir(str(home / 'snoop'))
            execv([waitress] + argv[2:] + ['snoop.site.wsgi:application'])

    if argv[:1] == ['snoop']:
        py = str(home / 'venvs' / 'snoop' / 'bin' / 'python')
        manage_py = str(home / 'snoop' / 'manage.py')
        execv([py, manage_py] + argv[1:])

    if argv[:1] == ['search']:
        py = str(home / 'venvs' / 'search' / 'bin' / 'python')
        manage_py = str(home / 'search' / 'manage.py')
        execv([py, manage_py] + argv[1:])

    raise RuntimeError("Unknown command {!r}".format(argv))

if __name__ == '__main__':
    main(sys.argv[1:])
