popen
=====

A shell like DSL front for subprocess.Popen

Usage
-----

Simples usage, run a command and iterate the output lines:

```py
from popen import Sh
for line in Sh('ls', '-la', '~'):
    print line
```

Piping that output to a file:

```py
Sh('ls', '-la', '~') > '~/listing'
```

Note that special characters like `~` is expanded, as are environment
variables (e.g. `$HOME`).

Chaining commands is trivial, here with append instead of write to file:

```py
Sh('ls') | Sh('sort') >> '~/listing'
```

But the right hand side of `|` can be very flexible, as it employs
lexical splitter on string input or takes an iterable:


```py
Sh('ls', '-la', '~') | 'sort -c' | ['uniq', '-c'] | 'tail' | Sh('wc') > '~/listing'
```

To run a command and let output go to `stdout`, ask for the return code:

```py
cmd = Sh('ls') | 'grep polka'
print cmd.returncode
```

