def question(label, default):
    rv = input("{} [{}]: ".format(label, default))
    return rv.strip() or default

def main():
    rv = question("Installation folder", '/opt/hoover')
    print(repr(rv))

if __name__ == '__main__':
    main()
