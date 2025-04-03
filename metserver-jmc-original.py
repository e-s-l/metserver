#!/usr/bin/python
import socket
import serial
from threading import Timer 
from thread import *
HOST = ''   # Symbolic name, meaning all available interfaces
PORT = 30384 # Arbitrary non-privileged port
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print 'Socket created'
semaphore=0

#Bind socket to local host and port
try:
    s.bind((HOST, PORT))
except:
    print 'Bind failed. Error Code : ' + socket.error[0] + ' Message ' + socket.error[1]
    sys.exit()
     
print 'Socket bind complete'

#Start listening on socket
s.listen(0)
print 'Socket now listening'

class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False




def getmet():
  global semaphore
  global readmsg
  # open serial port & send message
  #read back
  semaphore=1
  ser=serial.Serial('/dev/ttyUSB0', 9600, bytesize=8, parity='N', timeout=2)
  ser.write('*0100TT'+'\r'+'\n')
  tempmsg=ser.read(256)
  print tempmsg
  ser.write('*0100P3'+'\r'+'\n')
  presmsg=ser.read(256)
  print presmsg
  ser.write('*0100RH'+'\r'+'\n')
  rhmsg=ser.read(256)
  print rhmsg 
  ser.close()
  semaphore=0
  readmsg=tempmsg[5:256].split()[0]+','+presmsg[5:256].split()[0]+','+rhmsg[5:256].split()[0]+',-1,-1'
  print 'New readmsg = ' + readmsg
  return

def clientthread(conn,msg):
    global semaphore
    #Sending message to connected client
    #conn.send('Welcome to the server. Type something and hit enter\n') #send only takes string
     
    #infinite loop so that function do not terminate and thread do not end.
    #Receiving from client
    #readmsg=getmet()
    conn.sendall(msg)
    #came out of loop
    conn.close()
 
#now keep talking with the client
global readmsg
getmet()
RepeatedTimer(20,getmet).start()
while 1:
  #wait to accept a connection - blocking call
  conn, addr = s.accept()
  print 'Connected with ' + addr[0] + ':' + str(addr[1])
  #start new thread takes 1st argument as a function name to be run, second is the tuple of arguments to the function.
  conn.sendall(readmsg)
  #conn.close()
  
  #clientthread(conn)
#  s.close()
#  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#  try:
#    s.bind((HOST, PORT))
#  except:
#    print 'Bind failed. Error Code : ' + socket.error[0] + ' Message ' + socket.error[1]
#    sys.exit()  
#  s.listen(0)
    
s.close()
