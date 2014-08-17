# -*- coding:utf-8 -*-
import os

PID_FILE = '/tmp/heimdall.pid'
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

STDERR = '/dev/null'
STDOUT = '/dev/null'

HTTP_BIND = ('', 9090)


def dummy_command(webhook, headers):
    tmp = "headers: %s\n" % headers
    tmp += "webhook: %s" % webhook
    return tmp


def ping_event(webhook, headers):
    return 'Got: %s' % webhook['zen']


HOOKS = {
    'github': {
        'push': {
            '<you_username>/<repo_name>': {
                'command': dummy_command,
            },
        },
        'ping': {
            'command': ping_event,
        },
    },
    'travis': {
        'push': {
            '<you_username>/<repo_name>': {
                'command': dummy_command,
            },
        },
    }
}
