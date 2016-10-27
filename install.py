import sys
import os
from pathlib import Path
import subprocess

SETUP_REPO = 'https://github.com/hoover/setup.git'

def question(label, default):
    rv = input("{} [{}]: ".format(label, default))
    return rv.strip() or default

def main():
    home = Path(question("Installation folder", str(Path.cwd() / 'hoover')))
    if home.is_dir() and len(list(home.iterdir())) > 0:
        raise RuntimeError("Installation folder exists and is not empty")
    home.mkdir(exist_ok=True)

    subprocess.check_call(['git', 'clone', SETUP_REPO], cwd=str(home))
    args = [
        sys.executable,
        str(home / 'setup' / 'hoover_script.py'),
        'bootstrap',
    ]
    os.execve(args[0], args, dict(os.environ, HOOVER_HOME=str(home)))

if __name__ == '__main__':
    main()
