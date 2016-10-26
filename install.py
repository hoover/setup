import sys
import subprocess
from pathlib import Path
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from urllib.request import urlretrieve

VIRTUALENV_URL = 'https://github.com/pypa/virtualenv/raw/master/virtualenv.py'
SETUPTOOLS_URL = 'https://pypi.python.org/packages/8a/1f/e2e14f0b98d0b6de6c3fb4e8a3b45d3b8907783937c497cb53539c0d2b19/setuptools-28.6.1-py2.py3-none-any.whl'
PIP_URL = 'https://pypi.python.org/packages/9c/32/004ce0852e0a127f07f358b715015763273799bd798956fa930814b60f39/pip-8.1.2-py2.py3-none-any.whl'
SEARCH_REPO = 'https://github.com/hoover/search.git'
SNOOP_REPO = 'https://github.com/hoover/snoop.git'
UI_REPO = 'https://github.com/hoover/ui.git'

def question(label, default):
    rv = input("{} [{}]: ".format(label, default))
    return rv.strip() or default

def runcmd(cmd, **kwargs):
    subprocess.check_call([str(c) for c in cmd], **kwargs)

@contextmanager
def tmp_virtualenv():
    with TemporaryDirectory() as _tmp:
        def download(url, directory):
            name = url.split('/')[-1]
            urlretrieve(url, str(directory / name))

        def run(*args):
            cmd = (
                sys.executable,
                tmp / 'virtualenv.py',
                '--extra-search-dir={}'.format(tmp),
            )
            runcmd(cmd + args)

        tmp = Path(_tmp)
        download(VIRTUALENV_URL, tmp)
        download(SETUPTOOLS_URL, tmp)
        download(PIP_URL, tmp)
        yield run

def clone_git(url, directory):
    runcmd(['git', 'clone', url], cwd=str(directory))

def main():
    home = Path(question("Installation folder", str(Path.cwd() / 'hoover')))
    if home.is_dir() and len(list(home.iterdir())) > 0:
        raise RuntimeError("Installation folder exists and is not empty")
    home.mkdir(exist_ok=True)

    with tmp_virtualenv() as create_virtualenv:
        create_virtualenv(home / 'venvs' / 'search')
        create_virtualenv(home / 'venvs' / 'snoop')

    clone_git(SEARCH_REPO, home)
    clone_git(SNOOP_REPO, home)
    clone_git(UI_REPO, home)

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

if __name__ == '__main__':
    main()
