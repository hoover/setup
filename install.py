from pathlib import Path

def question(label, default):
    rv = input("{} [{}]: ".format(label, default))
    return rv.strip() or default

def main():
    home = Path(question("Installation folder", str(Path.cwd() / 'hoover')))
    if home.is_dir() and len(list(home.iterdir())) > 0:
        raise RuntimeError("Installation folder exists and is not empty")
    home.mkdir(exist_ok=True)

if __name__ == '__main__':
    main()
