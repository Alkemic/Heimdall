#!/usr/bin/env python
# -*- coding:utf-8 -*-
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import json
from subprocess import call

import sys
import os
import time
import atexit
import signal
import urlparse

import config

__author__ = 'Daniel Alkemic Czuba <dc@danielczuba.pl>'



class Daemon(object):
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
    """
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null',
                 stderr='/dev/null', working_dir='/'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
        self.working_dir = working_dir

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # decouple from parent environment
        os.chdir(self.working_dir)
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

            # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pidfile
        atexit.register(self.delpid)
        pid = str(os.getpid())
        file(self.pidfile, 'w+').write("%s\n" % pid)

    def delpid(self):
        os.remove(self.pidfile)

    def get_pid(self):
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        return pid

    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            message = "Pidfile %s already exist. Daemon already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        pid = self.get_pid()

        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            sys.stderr.write(message % self.pidfile)
            return  # not an error in a restart

        # Try killing the daemon process
        try:
            while 1:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """
        pass


class GitHubRequestHandler(BaseHTTPRequestHandler):
    """
    Handler
    """
    hooks = {}

    def do_POST(self):
        webhook = self.parse_webhook()
        event = self.headers.getheader('X-GitHub-Event', False)
        command = False

        if not event or event not in self.hooks:
            self.send_response(404)
            return

        if 'command' in self.hooks[event]:
            command = self.hooks[event]['command']

        if not command:
            if 'repository' not in webhook or 'full_name' not in webhook['repository']:
                self._respond(404)
                return
            else:
                command = self.hooks[webhook['repository']['full_name']]['command']

                if not isinstance(command, (tuple, list, dict, set, frozenset)):
                    command = command,

        try:
            to_respond = ''
            try:
                if callable(command):
                    to_respond = command(webhook, self.headers)
                else:
                    # It's quite insecure, but I belive whoever is using this, knows 
                    # that using this can fuck things pretty serious
                    for cmd in command:
                        call(cmd, shell=True)  

                self._respond()
                self.wfile.write(to_respond)
            except (OSError, CalledProcessError):
                self._respond(500)

            self.wfile.close()
        except Exception as e:
            print e
            self._respond(500)

    def get_body(self):
        length = int(self.headers.getheader('content-length'))
        body = self.rfile.read(length)
        return body

    def parse_webhook(self):
        """
        Parse request data sent from GitHub to our service and return payload
        """
        body = self.get_body()
        try:
            post = urlparse.parse_qs(body)
            payload = post['payload']
        except KeyError:
            payload = body

        payload = json.loads(payload)

        return payload

    def _respond(self, code=200):
        self.send_response(code)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()


class GitHubAutoDeployDaemon(Daemon):
    """
    Main daemon class
    """

    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null',
                 stderr='/dev/null', working_dir='/'):

        super(GitHubAutoDeployDaemon, self)\
            .__init__(pidfile, stdin, stdout, stderr, working_dir)

    def run(self):
        GitHubRequestHandler.hooks = config.HOOKS  # todo: make it more clean
        listener = HTTPServer(config.HTTP_BIND, GitHubRequestHandler)
        listener.serve_forever()


def main():
    daemon = GitHubAutoDeployDaemon(
        config.PID_FILE,
        stdout=config.STDOUT,
        stderr=config.STDERR,
    )

    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
            print 'Starting daemon \'%s\', pid: %i' % (sys.argv[0], daemon.get_pid())
        elif 'stop' == sys.argv[1]:
            daemon_pid = daemon.get_pid()
            if daemon_pid is not None:
                print 'Stopping daemon \'%s\', pid: %i' % (sys.argv[0], daemon.get_pid())
            else:
                print 'Error during stopping daemon!'
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon_pid = daemon.get_pid()
            if daemon_pid is not None:
                print 'Restarting daemon \'%s\', pid: %i' % (sys.argv[0], daemon.get_pid())
            else:
                print 'Error during restarting daemon!'
            daemon.restart()
        elif 'status' == sys.argv[1]:
            daemon_pid = daemon.get_pid()
            if daemon_pid is not None:
                print 'Daemon is running, pid: %i' % daemon.get_pid()
            else:
                print 'Daemon is not running.'
        else:
            print 'Unknown command'
            sys.exit(2)
        sys.exit(0)
    else:
        print 'usage: %s start|stop|restart|status' % sys.argv[0]
        sys.exit(2)


if __name__ == '__main__':
    main()
