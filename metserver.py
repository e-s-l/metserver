#!/usr/bin/env python3

"""
This is a rewrite of JMc's py2 version of the original metserver.c program.
It samples the weather station (wx) at a low cadence & sends this value when a client connects.

ESL, 20.1.2025

Notes:
- The original getmet.c in the field system initialises the values thus:
    temp=-51.0; pres=-1.0; humi=-1.0; wsp=-1.0; wdir=-1;
    We do the same.
- From the original, the wind units are:
    wdir - azimuth wind direction, degrees
    wsp  - wind speed, m/s
"""

import ipaddress                                    # to validate the hosts.
import socket                                       # for tcp connects.
import time                                         # for the optional throttle.
from concurrent.futures import ThreadPoolExecutor   # for multithreading the client connections.
from threading import Timer, Lock                   # for the regular sampling of the wx.
import serial                                       # for communicating with the wx.
from config import *                                # program parameters

###########
# classes #
###########

class RepeatedTimer(object):
    """JMc's class to create an x interval timer
    which runs a function to poll the weather station."""

    def __init__(self, interval, function, *args, **kwargs):
        self.lock = Lock()
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        with self.lock:
            self.is_running = False
            self.start()
            self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        if self._timer:
            self._timer.cancel()
        self.is_running = False

#############
# functions #
#############

def setup_socket(h: str, p: int) -> socket:
    """
    Set up a TCP socket, bind it & prepare it to listen for incoming connections.

    :param h: host address (ipv4)
    :param p: port
    :return: socket
    """

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if debug: logger.info('Socket created')

        # Bind socket to local host and port
        try:
            s.bind((h, p))
            logger.info('Bind complete.')
        except Exception as e:
            raise Exception(f'Bind failed: {e}') from e

        # Start listening on socket
        s.listen(10)
        # parameter above is number of queued connections (the backlog)
        logger.info('Socket now listening.')

        return s

    except Exception as e:
        raise Exception(f'Exception in setting up the socket: {e}') from e

##########################

def poll_tcp() -> list:
    """
    To get the met data over tcp via a serial-2-ethernet device.

    This is just a place-holder until we set up the device.

    :return: string containing wx data, or read_err if there is an error.
    """

    try:
        with socket.create_connection((s2e_h, s2e_p), timeout=5) as s2e_sock:
            s2e_sock.sendall(b'*0100TT\r\n')
            tempmsg = s2e_sock.recv(256).decode('utf-8').strip()

            s2e_sock.sendall(b'*0100P3\r\n')
            presmsg = s2e_sock.recv(256).decode('utf-8').strip()

            s2e_sock.sendall(b'*0100RH\r\n')
            rhmsg = s2e_sock.recv(256).decode('utf-8').strip()

        return [tempmsg[5:].split()[0],presmsg[5:].split()[0],rhmsg[5:].split()[0]]

    except Exception as e:
        logger.error(f"Error in poll_tcp: {e}")
        return met_err


def poll_serial() -> list:
    """
    Get the met data via the serial port.

    :return:  string containing wx data or a dummy set of -1s if there's an error
    """

    if debug: logger.debug("in poll_serial")

    try:
        with serial.Serial(port=comport, baudrate=baud, bytesize=bytesize, parity=parity) as ser:

            ser.timeout = timeout

            ###

            def read_command(command):
                """
                Send a command to the serial device and read the response.

                :param command: See the met4 manual.
                :return: The wx response value.
                """
                try:
                    ser.write(command)
                    response = ser.read_until(b'\r\n')

                    if not response or len(response.strip()) < 5:
                        raise ValueError(f"Invalid response: {response}")

                    return response.decode('utf-8').strip()

                except serial.SerialTimeoutException:
                    raise TimeoutError(f"Timeout while waiting for response to {command.decode('utf-8').strip()}")

                except Exception as ex:
                    raise Exception(f"Error during serial communication: {ex}")

            ###

            tempmsg = read_command(b'*0100TT\r\n')
            presmsg = read_command(b'*0100P3\r\n')
            rhmsg = read_command(b'*0100RH\r\n')

        return [tempmsg[5:].split()[0],presmsg[5:].split()[0],rhmsg[5:].split()[0]]

    except ValueError as ve:
        logger.error(f"Value error in poll_serial: {ve}")
        return met_err

    except serial.SerialException as se:
        logger.error(f"Serial exception: {se}")
        return met_err

    except TimeoutError as te:
        logger.error(f"Timeout error in poll_serial: {te}")
        return met_err

    except Exception as e:
        logger.error(f"Unexpected error in poll_serial: {e}")
        return met_err


def get_met() -> list:
    """
    Runner function to get the met data (temp, pressure, humidity).

    :return: The list of met data.
    """

    if debug: logger.debug("in get_met")

    if s2e_mode:
        # try the s2e socket...
        met_data = poll_tcp()
        # then if no result give the com port a go...
        if met_data == met_err and serial_mode:
            met_data = poll_serial()
    elif serial_mode:
        met_data = poll_serial()

    if debug: logger.debug(met_data)

    return met_data

##########################

def anemometer_connect() -> socket:
    """
    Copied from Jamie's MutlicastCapture.py

    :return: socket for connection
    """

    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

    # Allow multiple sockets to use the same PORT number
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)

    # Bind to the port that we know will receive multicast data
    sock.bind((ANY,MCAST_PORT))

    # Tell the kernel that we want to add ourselves to a multicast group
    # The address for the multicast group is the third param
    status = sock.setsockopt(socket.IPPROTO_IP,
    socket.IP_ADD_MEMBERSHIP,
    socket.inet_aton(MCAST_ADDR) + socket.inet_aton(ANY))
    # setblocking(0) is equiv to settimeout(0.0) which means we poll the socket.
    # But this will raise an error if recv() or send() can't immediately find or send data.
    sock.setblocking(0)

    return sock

def anemometer_read(s: socket, offset: int) -> list:
    """
    Adapted from Lucas' stream_wind.py

    :return: 2 element list of wind data (speed, direction).
    """

    attempts = 3
    while attempts > 0:
        try:
            data, addr = s.recvfrom(1024)

            vals = data.decode("utf-8").split(",")
            wsp = round(float(vals[4]), 2)
            wdir = round(float(vals[2]) + offset, 2)

            if debug: logger.info(f"{wsp} [m/s], dir = {wdir} [\u00b0]")

            return [str(wsp), str(wdir)]

        except socket.error as se:
            logger.warning(f"Socket error: {se}. I'll wait a second then retry. {attempts-1} attempts left.")
            time.sleep(1)
            attempts -= 1

        except ValueError as ve:
            logger.error(f"Error: {ve}")
            time.sleep(1)
            break

    return wind_err


def get_wind() -> list:
    """
    Connect to the NMEA multicasting anemometer interface,
    and get a value for the wind.
    Format: ([m/s],[direction])

    :return: 2 element list of wind data (speed, direction).
    """

    return anemometer_read(anemometer_connect(), misalignment)
    # should we be closing this off?
    # maybe, i dunno, not gonna touch it

##########################

def get_wx() -> list:
    """
    A wrapper to the scripts that poll for weather data.
    Concats the two list's into one.

    :return: the wx data, a 5 element list like (temp, press, humid, speed, direction). Will be converted to a string later down the line.
    """

    try:
        # cat list of 3 (temp, press, humid) w/ list of 2 (w_speed, w_direct)
        wx_data = get_met() + get_wind()

    except Exception as e:
        logger.error(f"Error gathering the wx data: {e}")
        wx_data = met_err + wind_err

    if debug: logger.info(f"{wx_data}")
    return wx_data

##########################

def client_handler(conn, readmsg_lock, data: dict):
    """
    When a client connects on the socket, return the wx data string.

    :param conn: The socket connection.
    :param readmsg_lock: A thread lock.
    :param readmsg: The wx data string.
    :return: None
    """

    if debug: logger.debug(f"in client handler")

    try:
        with readmsg_lock:
            msg = ','.join(str(x) for x in data["msg"]).encode('utf-8')

        conn.sendall(msg)

    except Exception as e:
        raise Exception(f'Error in client_handler: {e}') from e
    finally:
        # properly close off the connection
        # V1, needs this to stop connection ballooning
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER)
        # V2, maybe unnecessary
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            if debug: logger.debug(f"OSERROR occured closing socket!")
            pass
        except Exception as e:
            if debug: logger.debug(f"exception while closing socket: {e}")
            pass
        # why not both!

        conn.close()
        if debug: logger.info("Connection closed.")


def check_config():
    """
    Quick validity check of the config file.
    Completely unnecessary.

    :return: None
    """

    # check one of the input modes is true
    if not (s2e_mode or serial_mode): 
        raise Exception("no wx input configured")

    # check hosts are valid ipv4s
    try:
        ipaddress.ip_address(s2e_h)
    except ValueError as ve:
        raise Exception(f'invalid s2e host address: {s2e_h}') from ve


def setup_server():
    """
    Given a valid configuration, create a server, start a timer regularly reading the wx data, and start the main loop.

    :return: None
    """

    sock = None
    rt = None

    try:

        # check config settings are ok
        check_config()

        #################
        # create socket #
        #################

        # host & port stored in config file
        try:
            sock = setup_socket(host, port)
        except Exception as e:
            raise Exception(f"Error creating socket: {e}") from e

        ###################
        # set up readings #
        ###################

        data = {"msg": get_wx()}
        readmsg_lock = Lock()

        #####################

        def update_readmsg():
            """
            Update the globally held value of the wx data string.
            To be regularly re-run by the timer.

            :return: None
            """

            try:
                new_msg = get_wx()
                with readmsg_lock:
                    data["msg"] = new_msg
            except Exception as ex:
                raise Exception(f"Error reading sensor: {ex}") from ex

        #####################

        rt = RepeatedTimer(rt_time, update_readmsg)

        with ThreadPoolExecutor(max_workers=10) as executor:
            main_loop(sock, executor, rt, data, readmsg_lock)

    except  Exception as e:
        raise Exception(f"Exception setting up the server: {e}") from e


def server_shutdown(s: socket, rt: RepeatedTimer):
    """
    Helper function to cleanly kill the server program.

    :param s: the socket to close.
    :param rt: the timer to abort.
    :return:  None
    """

    try:
        if rt:
            rt.stop()
        if s:
            s.close()
        if debug: logger.info("Server shut down.")
    except Exception as e:
        raise Exception(f'Exception while shutting down server.') from e


def main_loop(s: socket, executor, repeat_timer: RepeatedTimer, msg: dict, lock):
    """
    the main loop run in the server which gives
    the wx value (read_msg) to any new connections & closes the connection.

    :param s: the socket to listen to.
    :param executor: the thread pool execution agent.
    :param repeat_timer: the timer handling the updates of the wx reads.
    :param msg: the current wx data.
    :param lock: a lock.
    :return:  None
    """

    try:
        # in which we accept connections (from FS/the client) & return an immediate reading
        while True:
            try:
                # wait to accept a connection - blocking call
                conn, addr = s.accept()
                if debug: logger.info(f'Connected with {addr[0]} : {addr[1]}')

                # new thread to handle each client
                executor.submit(client_handler, conn, lock, msg)

                # mostly for debuggin'
                if throttle:
                    time.sleep(0.01)

            except OSError as os_err:
                raise Exception(f"Socket error: {os_err}") from os_err
            except Exception as e:
                raise Exception(f"Error in main loop: {e}") from e

    except KeyboardInterrupt:
        logger.info("Shutting down server...")
    finally:
        server_shutdown(s, repeat_timer)

############################

if __name__ == "__main__":
    try:
        sys.exit(setup_server())
    except Exception as exc:
        logger.error(f"{exc}")
        sys.exit(1)
