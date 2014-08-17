#!/usr/bin/env python
# -*- coding:utf-8 -*-
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import json
from subprocess import call, CalledProcessError

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
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (
                e.errno,
                e.strerror
            ))
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
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (
                e.errno,
                e.strerror
            ))
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
        """Deletes pidfile"""
        os.remove(self.pidfile)

    def get_pid(self):
        """Returns pid"""
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
            pf = file(self.pidfile, 'r')
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
        You should override this method when you subclass Daemon. It will be
        called after the process has been
        daemonized by start() or restart().
        """
        pass


class WebHookRequestHandler(BaseHTTPRequestHandler):
    """
    Handler
    """
    hooks = {}

    _webhook = None

    @property
    def webhook(self):
        """Return hook data"""
        if self._webhook is None:
            body = self.get_body()
            try:
                post = urlparse.parse_qs(body)
                webhook = post['payload']
            except KeyError:
                webhook = body

            self._webhook = json.loads(webhook)

        return self._webhook

    def _get_event(self):
        """Returns information about event"""
        event = self.headers.getheader('X-GitHub-Event', False)
        if event:
            sender = 'github'
            return sender, event

        is_travis = all((
            'build_url' in self.webhook, 'travis' in self.webhook['build_url']
        ))
        if is_travis:
            event = self.webhook['type']
            sender = 'travis'
            return sender, event

    def _get_repository_name(self):
        """Returns repository name"""
        try:
            return self.webhook['repository']['full_name']
        except KeyError:
            pass

        try:
            return "%s/%s" % (
                self.webhook['repository']['owner_name'],
                self.webhook['repository']['name'],
            )
        except KeyError:
            pass

        return None

    def do_POST(self):
        """Actually handler request"""
        sender, event = self._get_event()
        repository = self._get_repository_name()

        try:
            command = self.hooks[sender][event][repository]['command']
        except KeyError:
            try:
                command = self.hooks[sender][event]['command']
            except KeyError:
                self._respond(404, 'Unknown %s:%s:%s' % (
                    sender,
                    event,
                    repository,
                ))
                return

        try:
            to_respond = ''
            try:
                if callable(command):
                    to_respond = command(self.webhook, self.headers)
                else:
                    # It's quite insecure, but I believe whoever is using this,
                    # knows that using this can fuck things pretty serious
                    for cmd in command:
                        call(cmd, shell=True)

                self._respond()
                if to_respond:
                    self.wfile.write(to_respond)
            except (OSError, CalledProcessError):
                self._respond(500)

            self.wfile.close()
        except Exception as e:
            print e
            self._respond(500)

    def get_body(self):
        """Returns request body"""
        length = int(self.headers.getheader('content-length'))
        body = self.rfile.read(length)
        return body

    def _respond(self, code=200, message=None):
        """Shortcut to make respond"""
        self.send_response(code)
        self.send_header('Content-type', 'text/plain')
        if message is not None:
            self.send_header('X-Heimdall-Message', message)
        self.end_headers()


def run_heimdall():
    """Run Heimdall end-point"""
    WebHookRequestHandler.hooks = config.HOOKS  # todo: make it more clean
    listener = HTTPServer(config.HTTP_BIND, WebHookRequestHandler)
    listener.serve_forever()


class HeimdallDaemon(Daemon):
    """
    Main daemon class
    """

    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null',
                 stderr='/dev/null', working_dir='/'):

        super(HeimdallDaemon, self)\
            .__init__(pidfile, stdin, stdout, stderr, working_dir)

    def run(self):
        """Run"""
        run_heimdall()


def main():
    daemon = HeimdallDaemon(
        config.PID_FILE,
        stdout=config.STDOUT,
        stderr=config.STDERR,
    )

    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
            print 'Starting daemon \'%s\', pid: %i' % (
                sys.argv[0],
                daemon.get_pid()
            )
        elif 'stop' == sys.argv[1]:
            daemon_pid = daemon.get_pid()
            if daemon_pid is not None:
                print 'Stopping daemon \'%s\', pid: %i' % (
                    sys.argv[0],
                    daemon.get_pid()
                )
            else:
                print 'Error during stopping daemon!'
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon_pid = daemon.get_pid()
            if daemon_pid is not None:
                print 'Restarting daemon \'%s\', pid: %i' % (
                    sys.argv[0],
                    daemon.get_pid()
                )
            else:
                print 'Error during restarting daemon!'
            daemon.restart()
        elif 'status' == sys.argv[1]:
            daemon_pid = daemon.get_pid()
            if daemon_pid is not None:
                print 'Daemon is running, pid: %i' % daemon.get_pid()
            else:
                print 'Daemon is not running.'
        elif 'fg' == sys.argv[1]:
            print 'Starting in foreground'
            run_heimdall()
        else:
            print 'Unknown command'
            sys.exit(2)
        sys.exit(0)
    else:
        print 'usage: %s start|stop|restart|status|fg' % sys.argv[0]
        sys.exit(2)


if __name__ == '__main__':
    main()
