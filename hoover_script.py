import sys

def main(argv):
    if argv == ['configure']:
        print("Hello from hooverscript!")
        return

    raise RuntimeError("Unknown command {!r}".format(argv))

if __name__ == '__main__':
    main(sys.argv[1:])
