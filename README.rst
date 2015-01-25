===========
popen
===========

-----------
What is it?
-----------

The ``popen`` package provides a simple shell-like syntax inside python for running
external commands.

Features:

* Chaining (aka. piping) as ``Sh('ls') | 'sort'``
* Redirect stderr to stdout as ``Sh('make').include_stderr | 'wc'``
* Redirect output to file as ``Sh('ls') > '~/listing.txt'``
* Iteration over output lines as ``for line in Sh('ls'):``
* Streaming input into commands in the chain as ``Sh('grep', '-q', 'code').stdin('~/listing.txt').returncode``
* Expands special characters (``~*!?``)
* Expands env vars (``$HOME``) as ``print Sh('ls', '$USER', '~/*')``
* Properly splits strings (``'echo "hole in one"'`` becomes ``['echo', 'hole in one']``)
* Or iterable arguments (``Sh('ls', '-l') | ['wc', '-l'] > '/dev/null'``)

=====
TL;DR
=====

Installation:

.. code-block:: SH

    pip install popen

Example:

.. code-block:: PY

    from popen import Sh
    for line in Sh('du', '~/') | 'head -n 10' | 'sort -n':
        print('GOT', line)

=====
Usage
=====

Simples usage, run a command and iterate the output lines:

.. code-block:: PY

    from popen import Sh
    for line in Sh('ls', '-la', '~'):
        print line

Piping that output to a file:

.. code-block:: PY

    Sh('ls', '-la', '~') > '~/listing'

Note that special characters like ``~`` are expanded, as are environment
variables (e.g. ``$HOME``).

Chaining commands is trivial, here with append instead of write to file:

.. code-block:: PY

    Sh('ls') | Sh('sort') >> '~/listing'

But the right hand side of ``|`` can be very flexible, as it employs
lexical splitter on string input or takes an iterable:


.. code-block:: PY

    Sh('ls', '-la', '~') | 'sort -c' | ['uniq', '-c'] | 'tail' | Sh('wc') > '~/listing'

To run a command and let output go to ``stdout``, ask for the return code:

.. code-block:: PY

    cmd = Sh('ls') | 'grep polka'
    print cmd.returncode

