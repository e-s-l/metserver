#!/usr/bin/env python3

"""
This is a rewrite of JMc's py2 version of the original metserver.c program.
It samples the weather station (wx) at a low cadence & sends this value when a client connects.
ESL, 20.1.2025
"""

import ipaddress                                    # to validate the hosts.
import socket                                       # for tcp connects.
import time                                         # for the optional throttle.
from concurrent.futures import ThreadPoolExecutor   # for multithreading the client connections.
from threading import Timer, Lock                   # for the regular sampling of the wx.
import serial                                       # for communicating with the wx.

from config import *                                # program parameters

###########
# objects #
###########

class RepeatedTimer(object):
    """JMc's class to create an x interval time
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

def setup_socket(h: str, p: int):
    """
    Set-up a TCP socket, bind it & prepare it to listen for incoming connections.

    :param h: host address (ipv4)
    :param p: port
    :return: socket
    """

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        logger.info('Socket created')

        # Bind socket to local host and port
        try:
            s.bind((h, p))
            logger.info('Bind complete.')
        except Exception as e:
            raise Exception(f'Bind failed.') from e

        # Start listening on socket
        s.listen(10) # parameter here is number of queued connections (the backlog)
        logger.info('Socket now listening.')

        return s

    except Exception as e:
        raise Exception(f'Exception in setting up the socket!\n{e}') from e

def poll_tcp():
    """
    To get the wx data over tcp via a serial-2-ethernet device.

    :return: string containing wx data, or `None` if
             there is an error.
    """
    try:
        with socket.create_connection((s2e_h, s2e_p), timeout=5) as s2e_sock:
            s2e_sock.sendall(b'*0100TT\r\n')
            tempmsg = s2e_sock.recv(256).decode('utf-8').strip()

            s2e_sock.sendall(b'*0100P3\r\n')
            presmsg = s2e_sock.recv(256).decode('utf-8').strip()

            s2e_sock.sendall(b'*0100RH\r\n')
            rhmsg = s2e_sock.recv(256).decode('utf-8').strip()

        return f"{tempmsg[5:].split()[0]},{presmsg[5:].split()[0]},{rhmsg[5:].split()[0]},-1,-1"

    except Exception as e:
        logger.error(f"Error in poll_tcp: {e}")
        return None


def poll_serial():
    """
    Get the wx data via the serial port.

    :return:  string containing wx data or a dummy set of -1s if there's an error
    """
    if debug: logger.debug("in poll_serial")

    try:
        with serial.Serial(com_port, baud_rate, bytesize, parity) as ser:

            ser.timeout = serial_timeout

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

            tempmsg = read_command(b'*0100TT\r\n')
            presmsg = read_command(b'*0100P3\r\n')
            rhmsg = read_command(b'*0100RH\r\n')

        return f"{tempmsg[5:].split()[0]},{presmsg[5:].split()[0]},{rhmsg[5:].split()[0]},-1,-1"

    except ValueError as ve:
        logger.error(f"Value error in poll_serial: {ve}")
        return rm_err

    except serial.SerialException as se:
        logger.error(f"Serial exception: {se}")
        return rm_err

    except TimeoutError as te:
        logger.error(f"Timeout error in poll_serial: {te}")
        return rm_err

    except Exception as e:
        logger.error(f"Unexpected error in poll_serial: {e}")
        return rm_err

def getmet():
    """
    Runner function to get the wx data.
    :return: The string of wx data.
    """
    if debug: logger.debug("in getmet")

    readmsg = "0,0,0,0,0"  # dummy initialisation value

    if s2e_mode:
        # try the s2e socket...
        readmsg = poll_tcp()
        # then if no result give the com port a go...
        if readmsg is None and serial_mode:
            readmsg = poll_serial()
    elif serial_mode:
        readmsg = poll_serial()

    if debug: logger.debug(readmsg)

    return readmsg


def client_handler(conn, readmsg_lock, readmsg: str):
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
            data = readmsg.encode('utf-8')

        conn.sendall(data)

    except Exception as e:
        raise Exception(f'Error in client_handler: {e}') from e
    finally:
        # properly close of the connection (needs this to stop connection ballooning.)
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER)
        conn.close()
        logger.info("Connection closed.")


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


def main():
    """
    Given a valid configuration, create a server, start a timer regularly reading the ex data
    give this value to any new connections & close the connection, & repeat.
    :return: None
    """
    ####
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

    readmsg = getmet()
    readmsg_lock = Lock()

    def update_readmsg():
        """
        Update the globally held value of the wx data string.
        To be regularly re-run by the timer.
        :return: None
        """
        nonlocal readmsg
        try:
            new_msg = getmet()
            with readmsg_lock:
                readmsg = new_msg
        except Exception as ex:
            raise Exception(f"Error reading sensor: {ex}") from ex

    rt = RepeatedTimer(20, update_readmsg)

    #######################
    # enter the main loop #
    #######################
    try:
        with ThreadPoolExecutor(max_workers=10) as executor:
            # in which we accept connections (from FS/the client) & return an immediate reading
            while True:
                try:
                    # wait to accept a connection - blocking call
                    conn, addr = sock.accept()
                    logger.info(f'Connected with {addr[0]} : {addr[1]}')

                    # new thread to handle each client
                    executor.submit(client_handler, conn, readmsg_lock, readmsg)

                    #
                    if throttle: time.sleep(0.01)

                except OSError as os_err:
                    raise Exception(f"Socket error: {os_err}") from os_err
                except Exception as e:
                    raise Exception(f"Error in main loop: {e}") from e

    except KeyboardInterrupt:
        logger.info("Shutting down server...")
    except Exception as e:
        raise Exception(f'Exception in main: {e}') from e
    finally:
        try:
            rt.stop()
            sock.close()
            logger.info("Server shut down.")
        except Exception as e:
            raise Exception(f'Exception while shutting down: {e}') from e


############################

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        logger.error(f"{exc}")
        sys.exit(1)

########
# TODO
# consider adding database uploader
# test!!!
# docstrings
########