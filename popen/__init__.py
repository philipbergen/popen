import glob
import itertools
import shlex
import sys

__author__ = 'pbergen'

import os
import subprocess

class ShResult(object):
    def __init__(self, tail):
        self._tail = tail
        self.stdout, self.stderr = self._tail._pop.communicate()



def read_some(fd):
    """ A non-blocking version of .readlines() that will iterate lines as they come
        but also returns strings without newlines, if that's all there is.
        :param fd: File to read from, sys.stdin for example.
        :returns: iterator over stream lines.
    """
    import fcntl
    import select
    # Make sure file doesn't block, so we can do .read()
    fcntl.fcntl(fd, fcntl.F_SETFL, fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK)
    fds = [fd]

    while True:
        ready, _, _ = select.select(fds, [], [])
        ready = ready[-1]
        data = ready.read()
        if not data:
            break
        data = data.split('\n')
        while len(data) > 1:
            yield data.pop(0) + '\n'
        if data[0]:
            yield data[0]


class Sh(object):
    def __str__(self):
        res = []
        t = self
        while t:
            res.append(repr(t))
            t = t._input
        return ' | '.join(res[::-1])

    def __repr__(self):
        c = [repr(self._cmd)] + [repr(arg) for arg in self._args]
        res = ['Sh(' + ', '.join(c) + ')']
        if self._cwd:
            res.append('chdir(%r)' % self._cwd)
        if self._env:
            res.append('env(' + ', '.join(['%s:%r' % (k,v) for k,v in self._env.iteritems()]) + ')')
        if self._err_to_out:
            res.append('err_to_out()')
        return '.'.join(res)

    def __init__(self, *cmd):
        self._stdin = None
        self._input = None
        self._output = None
        self._env = None
        self._err_to_out = False
        self._cwd = None
        self._pop = None
        if len(cmd) == 1:
            cmd = shlex.split(cmd[0])
        cmd = [os.path.expanduser(os.path.expandvars(arg)) for arg in cmd]
        self._cmd, self._args = cmd[0], cmd[1:]

    def env(self, **kw):
        if self._env is None:
            self._env = dict(os.environ)
        self._env.update(kw)
        return self

    def chdir(self, chdir):
        self._cwd = chdir
        return self

    def stdin(self, stdin):
        if type(stdin) in (str, unicode):
            stdin = open(stdin)
        self._stdin = stdin
        return self

    @property
    def include_stderr(self):
        self._err_to_out = True
        return self

    @property
    def returncode(self):
        if not self._pop:
            self > sys.stdout
        link = self
        while link:
            if link._pop:
                return link._pop.returncode
        return None

    def __gt__(self, other):
        self._stream_out(other)

    def __rshift__(self, other):
        self._stream_out(other, True)

    def __or__(self, other):
        if type(other) in (str, unicode):
            other = shlex.split(other)
        return self._sh(*other)

    def __iter__(self):
        self._run()
        return read_some(self._pop.stdout)

    def _sh(self, *cmd):
        res = Sh(*cmd)
        res._input = self
        self._output = res
        if self._env:
            res._env = dict(self._env)
        if self._cwd:
            res._cwd = self._cwd
        self._run()
        return res

    def _run(self, stdout=subprocess.PIPE):
        cwd = (self._cwd if self._cwd else os.getcwd()) + '/'
        def glob_or(expr):
            res = [expr]
            if '*' in expr or '?' in expr:
                if expr and expr[0] != '/':
                    expr = cwd + expr
                res = glob.glob(expr)
                if not res:
                    res = [expr]
            return res

        args = [glob_or(arg) for arg in self._args]
        stderr = subprocess.STDOUT if self._err_to_out else None
        stdin = self._stdin if self._input is None else self._input._pop.stdout
        self._pop = subprocess.Popen([self._cmd] + list(itertools.chain.from_iterable(args)),
                                     stdin=stdin, stdout=stdout, stderr=stderr,
                                     close_fds=True, cwd=self._cwd, env=self._env)

    def _stream_out(self, target, append=False):
        if type(target) in (str, unicode):
            target = os.path.expanduser(os.path.expandvars(target))
            target = open(target, 'a' if append else 'w')
        self._run(target)
        self._pop.wait()
