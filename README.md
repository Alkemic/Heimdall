# Heimdall

Heimdall is automatic daemon to take actions on given GitHub webhook

## Installation

* `git clone https://github.com/Alkemic/Heimdall.git`
* Copy config: `cp _config.py config.py`
* Configure: `nano config.py`
* Run server: `./heimdall.py start`
* Configure [webhooks on GitHub](https://developer.github.com/webhooks/) using adres `http://<your_ip>:<port>`
* 

## Configuration

The most important configuration part is held in config.HOOKS, where we keep information about supported hooks, and repos in this hook. You have to make `dict` like this bellow

```python
def deploy_webpage(webhook, headers):
    pass


def ping_event(webhook, headers):
    return 'Got: %s' % webhook['zen']


HOOKS = {
    'push':{
        'Alkemic/webpage': {
            'command': deploy_webpage,
        },
        'Alkemic/webrss': {
            'command': [
                'cd /var/www/webrss; git pull',
                'sudo supervisorctl restart webrss',
            ],
        },
    },
    'ping': {
        'command': ping_event,
    },
}
```

The command index held command to run on given hook/repo trigger, where there should be either a callback, or a list of string with commands that will be passed to [`subprocess.call`](https://docs.python.org/2/library/subprocess.html#subprocess.call) with param `shell=True` (`subprocess.call(<cmd>, shell=True)`), so be aware that this is setup in this way.

If you choose to use a callback, the the return from it will be send as a body response to hook call.
