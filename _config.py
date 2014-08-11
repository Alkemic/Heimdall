# -*- coding:utf-8 -*-
import os

PID_FILE = '/tmp/github_auto_deploy.pid'
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

STDERR = '/dev/null'
STDOUT = '/dev/null'

HTTP_BIND = ('', 9090)


def dummy_command():
    print 'dummy', __name__

REPOS = {
    'https://github.com/Alkemic/wkspl': {
        'cd /home/alkemic/wkspl/',
        dummy_command,
    },
}
