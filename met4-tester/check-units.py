#!/usr/bin/env python3

import serial
import sys

###########
# Control #
###########

set_units = False

############
# Com port #
############
com_port = '/dev/ttyUSB0'
baud_rate = 9600
bytesize=8
parity='N'
serial_timeout=2

def check_pressure(s):

    # pressure
    print("checking pressure units:")
    s.write(b'*0100UN\r\n')
    pu_response = s.read_until(b'\r\n').decode('utf-8').strip()
    print(pu_response)

    # unit code is last value of response
    pu_code = pu_response[-1]

    # c.f. the manual
    units = {
        '0': "user-defined",
        '1': "psi",
        '2': "hPa (mbar)",
        '3': "bar",
        '4': "kPa",
        '5': "MPa",
        '6': "in Hg",
        '7': "mmHg (tor)",
        '8': "mH20",
    }

    return units.get(pu_code, "Unknown")


def check_temp(s):

    # temperature
    print("checking temperature units:")
    s.write(b'*0100TU\r\n')
    tu_response = s.read_until(b'\r\n').decode('utf-8').strip()
    print(tu_response)

    # unit code is last value of response
    tu_code = tu_response[-1]

    # c.f. the manual
    units = {
        '0': "Celsius",
        '1': "Fahrenheit",
    }

    return units.get(tu_code, "Unknown")


def send_set_pressure(s):

    print("setting pressure units to mBar")
    s.write(b'*0100EW*0100UN=2\r\n')
    print("response:")
    print(s.read_until(b'\r\n').decode('utf-8').strip())


def send_set_temp(s):

    print("setting temperature units to celsius")
    s.write(b'*0100EW*0100TU=0\r\n')
    print("response:")
    print(s.read_until(b'\r\n').decode('utf-8').strip())


def main():

    try:
        with serial.Serial(com_port, baud_rate, bytesize, parity, serial_timeout) as ser:

            print("******************")
            print(f'{check_temp(ser)}')
            print(f'{check_pressure(ser)}')

            if set_units:

                print("******************")
                send_set_pressure(ser)
                send_set_temp(ser)

                print("******************")
                print(f'{check_temp(ser)}')
                print(f'{check_pressure(ser)}')

    except Exception as e:
        raise Exception(f"Error polling the serial port") from e

############################

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"{exc}")
        sys.exit(1)
