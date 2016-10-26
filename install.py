import sys
import subprocess
from pathlib import Path
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from urllib.request import urlretrieve

VIRTUALENV_URL = 'https://github.com/pypa/virtualenv/raw/master/virtualenv.py'
SETUPTOOLS_URL = 'https://pypi.python.org/packages/8a/1f/e2e14f0b98d0b6de6c3fb4e8a3b45d3b8907783937c497cb53539c0d2b19/setuptools-28.6.1-py2.py3-none-any.whl'
PIP_URL = 'https://pypi.python.org/packages/9c/32/004ce0852e0a127f07f358b715015763273799bd798956fa930814b60f39/pip-8.1.2-py2.py3-none-any.whl'
SETUP_REPO = 'https://github.com/hoover/setup.git'
SEARCH_REPO = 'https://github.com/hoover/search.git'
SNOOP_REPO = 'https://github.com/hoover/snoop.git'
UI_REPO = 'https://github.com/hoover/ui.git'

HOOVER_SCRIPT = """\
#!/bin/sh
cd '{setup}'
export HOOVER_HOME='{home}'
{python} hoover_script.py "$@"
"""

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

def git_clone(url, directory):
    runcmd(['git', 'clone', url], cwd=str(directory))

def main():
    home = Path(question("Installation folder", str(Path.cwd() / 'hoover')))
    if home.is_dir() and len(list(home.iterdir())) > 0:
        raise RuntimeError("Installation folder exists and is not empty")
    home.mkdir(exist_ok=True)

    with tmp_virtualenv() as create_virtualenv:
        create_virtualenv(home / 'venvs' / 'search')
        create_virtualenv(home / 'venvs' / 'snoop')

    git_clone(SETUP_REPO, home)
    git_clone(SEARCH_REPO, home)
    git_clone(SNOOP_REPO, home)
    git_clone(UI_REPO, home)

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

    print("Success! Next step: run `{} configure`".format(bin_hoover))

if __name__ == '__main__':
    main()
