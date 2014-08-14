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
HOOKS = {
    'push':{
        'Alkemic/webrss': {
            'command': dummy_command,
        },
    },
    'ping': {
        'command': ping_event,
    },
}
```
