import sys
import os
from pathlib import Path
import subprocess

SETUP_REPO = os.getenv('HOOVER_SETUP_REPO', 'https://github.com/hoover/setup.git')
SETUP_BRANCH = os.getenv('HOOVER_SETUP_BRANCH', 'master')

if os.getenv('HOOVER_HOME'):
    home = Path(os.getenv('HOOVER_HOME'))
else:
    home = Path.cwd() / 'hoover'

def main():
    if home.is_dir() and len(list(home.iterdir())) > 0:
        print("Installation folder {} exists and is not empty.".format(str(home)))
        print("Please specify a suitable path using the HOOVER_HOME environment variable.")
    home.mkdir(exist_ok=True)

    subprocess.check_call(['git', 'clone', SETUP_REPO], cwd=str(home))
    subprocess.check_call(['git', 'checkout', SETUP_BRANCH], cwd=str(home / 'setup'))
    args = [
        sys.executable,
        str(home / 'setup' / 'hoover_script.py'),
        'bootstrap',
    ]
    os.execve(args[0], args, dict(os.environ, HOOVER_HOME=str(home)))

if __name__ == '__main__':
    main()
