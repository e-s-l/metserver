###########################
# Configuration variables #
###########################
# for the weather station server

# for setting up the logger
import logging
import sys

###########
# Control #
###########
debug = True                # If true, program will print readmsg (wx) values

##########
# Server #
##########
host = ''                   # Symbolic name, meaning all available interfaces
port = 30384                # Arbitrary non-privileged port

#####################
# Serial-2-ethernet #
#####################
s2e_mode = False
serial_mode = True
s2e_h = "192.168.0.100"     # DUMMY # Host address of the serial2ethernet convertor (s2e)
s2e_p = 5000                # DUMMY # Port of the s2e

############
# Com port #
############
com_port = '/dev/ttyUSB0'
baud_rate = 9600
bytesize=8
parity='N'
serial_timeout=2

############
# Database #
############

##########
# Logger #
##########
logfile = "met_server.log"          # the log output file, should really be /var/log/something or /tmp/something
logger = logging.getLogger(__name__)
# format of the log messages:
logfmt = logging.Formatter("%(asctime)s-%(levelname)s: %(message)s", "%Y.%j.%H:%M:%S")
# set the format & make output go to stdout & the logfile:
logfile_handler = logging.FileHandler(logfile)
logfile_handler.setFormatter(logfmt)
logger.addHandler(logfile_handler)                      # to the file
logger.addHandler(logging.StreamHandler(sys.stdout))    # to standard out
logger.setLevel(logging.DEBUG)                          # set default level
