#!/usr/bin/env python3

import sys
import socket
import threading
from threading import Timer, Lock
import serial

from config import *

###########
# objects #
###########

class RepeatedTimer(object):
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

def setup_socket(host: str, port: int):

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print('Socket created')

        # Bind socket to local host and port
        try:
            s.bind((host, port))
        except:
            raise Exception(f'Bind failed. Error Code : {socket.error[0]} Message {socket.error[1]}')

        print('Socket bind complete')

        # Start listening on socket
        s.listen(5) # parameter here is number of queued connections
        print('Socket now listening')

        return s

    except Exception as e:
        print(f'Exception in setting up the socket!\n{e}')
        sys.exit()

def getmet_with_tcp():

    def poll_tcp():

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
            print(f"Error in poll_tcp: {e}")
            return None

    def poll_serial():

        try:
            with serial.Serial('/dev/ttyUSB0', 9600, bytesize=8, parity='N', timeout=2) as ser:
                ser.write(b'*0100TT\r\n')
                tempmsg = ser.read(256).decode('utf-8').strip()

                ser.write(b'*0100P3\r\n')
                presmsg = ser.read(256).decode('utf-8').strip()

                ser.write(b'*0100RH\r\n')
                rhmsg = ser.read(256).decode('utf-8').strip()

            return f"{tempmsg[5:].split()[0]},{presmsg[5:].split()[0]},{rhmsg[5:].split()[0]},-1,-1"

        except Exception as e:
            print(f"Error in poll_serial: {e}")
            return "-1,-1,-1,-1,-1"

    if s2e_mode:
        # try the s2e socket...
        readmsg = poll_tcp()
        # then if no result give the com port a go...
        if readmsg is None:
            readmsg = poll_serial()
    else:
        readmsg = poll_serial()

    return readmsg

def getmet():
    # open serial port & send message
    try:
        with serial.Serial('/dev/ttyUSB0', 9600, bytesize=8, parity='N', timeout=2) as ser:
            ser.write(b'*0100TT\r\n')
            tempmsg = ser.read(256).decode('utf-8').strip()

            ser.write(b'*0100P3\r\n')
            presmsg = ser.read(256).decode('utf-8').strip()

            ser.write(b'*0100RH\r\n')
            rhmsg = ser.read(256).decode('utf-8').strip()

        readmsg = f"{tempmsg[5:].split()[0]},{presmsg[5:].split()[0]},{rhmsg[5:].split()[0]},-1,-1"
        print(f'New readmsg = {readmsg}')
        return readmsg

    except Exception as e:
        print(f'Error in getmet: {e}')
        return "-1,-1,-1,-1,-1"

def client_handler(conn, readmsg_lock, readmsg):
    try:
        with readmsg_lock:
            conn.sendall(readmsg.encode('utf-8'))

    except Exception as e:
        print(f'Error in client_handler: {e}')
    finally:
        conn.close()

def main():

    #########
    # Notes
    # need two threads one to read wx, one to give to client
    #
    #########

    print("hello sailor")

    #################
    # create socket #
    #################

    # host & port stored in config file
    sock = setup_socket(host, port)

    ###################
    # set up readings #
    ###################

    readmsg = "0,0,0,0,0"
    readmsg_lock = Lock()

    def update_readmsg():
        nonlocal readmsg
        new_msg = getmet()
        with readmsg_lock:
            readmsg = new_msg

    rt = RepeatedTimer(20, update_readmsg)

    #######################
    # enter the main loop #
    #######################
    try:
        while 1:
            # in which we accept connections (from FS/the client) & return an immediate reading

            # wait to accept a connection - blocking call
            conn, addr = sock.accept()
            print(f'Connected with {addr[0]} : {addr[1]}')

            # new thread to handle each client
            threading.Thread(target=client_handler, args=(conn, readmsg_lock, readmsg)).start()

    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f'Exception in main: {e}')
    finally:
        rt.stop()
        sock.close()
        print("Server shut down.")

############################

if __name__ == "__main__":
    sys.exit(main())

########
# TODO
# swap prints for logger
# consider adding database uploader
# test!!!
# docstrings
#
########