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
# print extra info
debug = False

# dummy read msg values in cases of error:
met_err = [-51.0,-1.0,-1.0]
wind_err = [-1.0,-1]
# NOTE: these are the same as the initialisation values
# chosen to match the FS' getmet.c

# add a slight time delay:
throttle = False


###############
# Anenmometer #
###############

# hb sensor is 20 degrees misaligned
hb_offset = 20
cd_offest = 0
misalignment = hb_offset

# mutlicast properties
ANY = "0.0.0.0"
MCAST_ADDR = "239.192.0.4"
MCAST_PORT = 60004
# these are identical for hb & cd

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

log2file = False
log2stdout = True

logger = logging.getLogger(__name__)

if log2file:
    logfile = "met_server.log"  # the log output file, should really be /var/log/something or /tmp/something
    logfmt = logging.Formatter("%(asctime)s-%(levelname)s: %(message)s", "%Y.%j.%H:%M:%S")
    logfile_handler = logging.FileHandler(logfile)
    logfile_handler.setFormatter(logfmt)
    logger.addHandler(logfile_handler)

if log2stdout:
    stdfmt = logging.Formatter("%(levelname)s: %(message)s")
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(stdfmt)
    logger.addHandler(stdout_handler)

logger.setLevel(logging.DEBUG)      # set default level
