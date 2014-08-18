# -*- coding:utf-8 -*-
import os
import logging as log

PID_FILE = '/tmp/heimdall.pid'
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

STDERR = '/dev/null'
STDOUT = '/dev/null'

LOG_FILE = os.path.join(PROJECT_ROOT, 'heimdall.log')

log.basicConfig(
    filename=LOG_FILE,
    level=log.DEBUG,
)

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
