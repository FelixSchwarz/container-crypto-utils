
import sys


__all__ = ['print_error']

def print_error(s):
    if isinstance(s, bytes):
        try:
            s = s.decode('UTF-8')
        except UnicodeDecodeError:
            print('error while decoding %r' % s)
            sys.exit(5)
    sys.stderr.write(s + '\n')

