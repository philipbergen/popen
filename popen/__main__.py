'''
This module serves not purpose besides being a testing crutch for my
as I develop popen.
'''
from . import Sh

if __name__ == '__main__':
    # This is a test
    Sh.debug = True
    if Sh('ls') | 'sort':
        print "OK"
    if Sh('make').include_stderr | 'wc':
        print "OK"
    Sh('ls') > '~/listing.txt'
    (Sh('wc') < '~/listing.txt').returncode
    for line in Sh('ls', '-la', '~'):
        print "GOT", line
    print "OK", Sh('grep', '-q', 'code').stdin('~/listing.txt').returncode
    print Sh('ls', '$USER', '~/*'), Sh('echo "hole in one"')
    Sh('ls', '-l') | ['wc', '-l'] > '/dev/null'
    for line in Sh('du', '~/') | 'head -n 10' | 'sort -n':
        print('GOT', line)

    Sh('ls') > 'polka'
    print (Sh('cat', '*py') | 'wc').returncode
    Sh('wc').stdin('polka').returncode

    s = Sh('ls') | ['grep', 'blt'] | 'wc "-l"'
    print s, s.returncode

    print "OK", Sh('ls').read()
    print "OK", Sh('ls').readlines()