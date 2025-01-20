# README

## About

This is a rewrite of JMc's py2 version of the original metserver.c program.

Mainly, motivated by updating to py3 but modified to include logger, lots of try catch clauses and raised exceptions (probably an unnecessary amount of them), and the probable adoption of a networked serial-to-ethernet convertor.

Now also requires an external configuration file (config.py).


## Project

Files: 

metserver.py, config.py, requirements.txt, README.md...


## Set-up

Some preliminaries:
```commandline
sudo apt upgrade
sudo apt-get install python3-pip 
sudo apt-get install python3-venv
```

### Set-up the virtual environment

```commandline
$ python3 -m venv venv
$ source venv/bin/activate
(venv) $ pip install -r requirements.txt
```

### Set-up the system service

```commandline
$ sudo cp metserver.service /etc/systemd/system/
$ sudo systemctl enable metserver.service
$ sudo systemctl start metserver.service
```

And check the logs:

```sudo journalctl -u metserver.service -f -n```

## Usage
