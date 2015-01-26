'''Shell-like DSL for subprocess.Popen calls.

Usage:
    Sh(CMD) [< INFILE] [| CMD]... [(>|>>) FILE]

CMD is one of:
* Sh('ls', '-la')
* 'ls -la'
* ['ls, '-la']

FILE and INFILE is:
* file like object
* filename

All arguments (CMD, FILE, INFILE) may contain special characters for expansion
such as `~?*!` and environment variables such as `$HOME`.

NOTE: If a command is not evaluated it is not run. A command is evaluated when
it is piped, redirected, returncode is checked (truth evaluation) or string
evaluation.
'''

import os
import subprocess
import glob
import itertools
import shlex
import sys
import fcntl
import select

def read_some(fd):
    """ A non-blocking version of .readlines() that will iterate lines as they
        come but also returns strings without newlines, if that's all there is.
        :param fd: File to read from, sys.stdin for example.
        :returns: iterator over stream lines.
    """


class Sh(object):
    debug = False
    def __repr__(self):
        res = []
        t = self
        while t is not None:
            res.append(t._repr())
            t = t._input
        return ' | '.join(res[::-1])

    def _repr(self):
        c = [repr(self._cmd)] + [repr(arg) for arg in self._args]
        res = ['Sh(' + ', '.join(c) + ')']
        if self._cwd:
            res.append('chdir(%r)' % self._cwd)
        if self._env:
            res.append('env(' + ', '.join(['%s:%r' % (k,v) for k,v in self._env.iteritems()]) + ')')
        if self._err_to_out:
            res.append('err_to_out()')
        if self._stdin:
            res.append('stdin(%r)' % (getattr(self._stdin, 'name', self._stdin)))
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
        if self.debug:
            print "*** DEBUG: Sh(%r, %r)" % (self._cmd, self._args)

    def env(self, **kw):
        '''
        Allows adding/overriding env vars in the execution context.
        :param kw: Key-value pairs
        :return: self
        '''
        if self._env is None:
            self._env = dict(os.environ)
        self._env.update(kw)
        return self

    def chdir(self, chdir):
        '''
        Changes the current working directory in the execution context.
        :param chdir: Any directory
        :return: self
        '''
        self._cwd = chdir
        return self

    def stdin(self, stdin):
        '''
        Provides input the command.
        :param stdin: Filename or file-like object for reading.
        :return: self
        '''
        if type(stdin) in (str, unicode):
            stdin = open(os.path.expanduser(os.path.expandvars(stdin)))
        self._stdin = stdin
        return self

    @property
    def include_stderr(self):
        '''
        Redirects stderr output to stdout so that stdout includes stderr
        content as well.
        :return: self
        '''
        self._err_to_out = True
        return self

    @property
    def returncode(self):
        '''
        Runs the command if it has not yet run (redirecting output to stdout).
        :return: The returncode of the last executed command in the chain.
        '''
        if not self._pop:
            self > sys.stdout
        link = self
        while link is not None:
            if link._pop:
                return link._pop.returncode
        return None

    def __bool__(self):
        return self.returncode == 0

    __nonzero__ = __bool__

    def __lt__(self, infile):
        '''
        Redirects infile to stdin of the command. Usually placed after the first
        command in the chain, not the last. Example:

            (Sh('sort') < '~/.bashrc') | 'tail'

        :param infile: Filename or file-like object for reading.
        :return: self
        '''
        self.stdin(infile)
        return self

    def __gt__(self, outfile):
        '''
        Writes stdout of the command into outfile.
        :param outfile: Filename or file-like object for writing.
        :return: The returncode
        '''
        return self._stream_out(outfile)

    def __rshift__(self, outfile):
        '''
        Appends stdout of the command into outfile.
        :param outfile: Filename or file-like object for writing.
        :return: The returncode
        '''
        self._stream_out(outfile, True)

    def __or__(self, cmd):
        '''
        Pipes the output of this command into cmd.
        :param cmd: String, iterable or Sh object
        :return:
        '''
        if type(cmd) in (str, unicode):
            cmd = shlex.split(cmd)
        if type(cmd) is Sh:
            return self._sh(cmd)
        return self._sh(*cmd)

    def __iter__(self):
        '''
        :return: Lines as they arrive, if line is incomplete, it is not
        newline terminated, please make sure to test for that.
        '''
        self._run()
        fd = self._pop.stdout
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

    def communicate(self):
        '''
        Similar to Popen.communicate it returns the stdout and stderr content.
        :return:(stdout, stderr)
        '''
        self._run()
        return self._pop.communicate()

    def read(self):
        '''
        Runs the command and reads all stdout.
        :return: All stdout as a single string.
        '''
        self._run()
        stdout, _ = self._pop.communicate()
        return stdout

    __str__ = read

    def readlines(self):
        '''
        Runs the command and reads all stdout into a list.
        :return: All stdout as a list of newline terminated strings.
        '''
        self._run()
        stdout, stderr = self._pop.communicate()
        return stdout.splitlines(True)

    def _sh(self, cmd, *args):
        '''
        Internal. Chains a command after this.
        :param cmd:
        :param args:
        :return: The new command.
        '''
        if not type(cmd) is Sh:
            cmd = Sh(cmd, *args)
        cmd._input = self
        self._output = cmd
        if self._env:
            cmd._env = dict(self._env)
        if self._cwd:
            cmd._cwd = self._cwd
        self._run()
        return cmd

    def _run(self, stdout=subprocess.PIPE):
        '''
        Internal. Starts running this command. Requires that there is an output configured
        beforehand and that all commands prior in the chain are running already.
        :param stdout: Where to send stdout.
        '''
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
        cmd = [self._cmd] + list(itertools.chain.from_iterable(args))
        if self.debug:
            print "*** DEBUG: Run", cmd
        self._pop = subprocess.Popen(cmd, stdin=stdin, stdout=stdout, stderr=stderr,
                                     close_fds=True, cwd=self._cwd, env=self._env)

    def _stream_out(self, outfile, append=False):
        '''
        Internal. Writes all stdout into outfile.
        :param outfile: Filename or file-like object for writing.
        :param append: Opens filename with append.
        :return: This command's returncode.
        '''
        if type(outfile) in (str, unicode):
            outfile = os.path.expanduser(os.path.expandvars(outfile))
            outfile = open(outfile, 'a' if append else 'w')
        self._run(outfile)
        self._pop.wait()
        return self.returncode