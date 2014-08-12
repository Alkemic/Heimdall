# -*- coding:utf-8 -*-
import os

PID_FILE = '/tmp/github_auto_deploy.pid'
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

STDERR = '/dev/null'
STDOUT = '/dev/null'

HTTP_BIND = ('', 9090)


def dummy_command(webhook, headers):
    print 'headers', headers
    print 'webhook', webhook


def ping_event(webhook, headers):
    return 'Got: %s' % webhook['zen']


HOOKS = {
    'push':{
        'Alkemic/wkspl': {
            'command': dummy_command,
        },
    },
    'ping': {
        'command': ping_event,
    },
}
