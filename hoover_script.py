import sys
import os
import random
import math
from pathlib import Path
from textwrap import dedent

_home = os.environ.get('HOOVER_HOME')
if not _home:
    raise RuntimeError("HOOVER_HOME environment variable is not set")
home = Path(_home)

def question(label, default):
    rv = input("{} [{}]: ".format(label, default))
    return rv.strip() or default

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
        HOOVER_ELASTICSEARCH_URL = {es_url!r}
    """)
    with local_py.open('w', encoding='utf-8') as f:
        f.write(template.format(**values))

def main(argv):
    if argv == ['configure']:
        configure_search()
        return

    raise RuntimeError("Unknown command {!r}".format(argv))

if __name__ == '__main__':
    main(sys.argv[1:])
