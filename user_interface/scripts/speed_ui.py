#!/usr/bin/env python

import rospy
import subprocess
from time import time, sleep, localtime

from wiringpi2 import wiringPiSetupGpio, pinMode, digitalRead, digitalWrite, GPIO
wiringPiSetupGpio()

if rospy.has_param('/speed_ui/clk'):
    CLK = rospy.get_param('/speed_ui/clk')
    
if rospy.has_param('/speed_ui/dio'):
    DIO = rospy.get_param('/speed_ui/dio')

"""
      A
     ---
  F |   | B
     -G-
  E |   | C
     ---
      D

"""


class TM1637:
    I2C_COMM1 = 0x40
    I2C_COMM2 = 0xC0
    I2C_COMM3 = 0x80
    digit_to_segment = [
        0b0111111, # 0
        0b0000110, # 1
        0b1011011, # 2
        0b1001111, # 3
        0b1100110, # 4
        0b1101101, # 5
        0b1111101, # 6
        0b0000111, # 7
        0b1111111, # 8
        0b1101111, # 9
        0b1110111, # A
        0b1111100, # b
        0b0111001, # C
        0b1011110, # d
        0b1111001, # E
        0b1110001  # F
        ]

    def __init__(self, clk, dio):
        self.clk = clk
        self.dio = dio
        self.brightness = 0x0f

        pinMode(self.clk, GPIO.INPUT)
        pinMode(self.dio, GPIO.INPUT)
        digitalWrite(self.clk, GPIO.LOW)
        digitalWrite(self.dio, GPIO.LOW)

    def bit_delay(self):
        sleep(0.001)
        return
   
    def set_segments(self, segments, pos=0):
        # Write COMM1
        self.start()
        self.write_byte(self.I2C_COMM1)
        self.stop()

        # Write COMM2 + first digit address
        self.start()
        self.write_byte(self.I2C_COMM2 + pos)

        for seg in segments:
            self.write_byte(seg)
        self.stop()

        # Write COMM3 + brightness
        self.start()
        self.write_byte(self.I2C_COMM3 + self.brightness)
        self.stop()

    def start(self):
        pinMode(self.dio, GPIO.OUTPUT)
        self.bit_delay()
   
    def stop(self):
        pinMode(self.dio, GPIO.OUTPUT)
        self.bit_delay()
        pinMode(self.clk, GPIO.INPUT)
        self.bit_delay()
        pinMode(self.dio, GPIO.INPUT)
        self.bit_delay()
  
    def write_byte(self, b):
      # 8 Data Bits
        for i in range(8):

            # CLK low
            pinMode(self.clk, GPIO.OUTPUT)
            self.bit_delay()

            pinMode(self.dio, GPIO.INPUT if b & 1 else GPIO.OUTPUT)

            self.bit_delay()

            pinMode(self.clk, GPIO.INPUT)
            self.bit_delay()
            b >>= 1
      
        pinMode(self.clk, GPIO.OUTPUT)
        self.bit_delay()
        pinMode(self.clk, GPIO.INPUT)
        self.bit_delay()
        pinMode(self.clk, GPIO.OUTPUT)
        self.bit_delay()

        return


def show_ip_address(tm):
    ipaddr = subprocess.check_output("hostname -I", shell=True, timeout=1).strip().split(b".")
    for octet in ipaddr:
        tm.set_segments([0, 0, 0, 0, 0, 0])
        sleep(0.1)
        tm.set_segments([tm.digit_to_segment[int(x) & 0xf] for x in octet])
        sleep(0.9)


def show_clock(tm):
    t = localtime()
    sleep(1 - time() % 1)
    d0 = tm.digit_to_segment[t.tm_hour // 10] if t.tm_hour // 10 else 0
    d1 = tm.digit_to_segment[t.tm_hour % 10]
    d2 = tm.digit_to_segment[t.tm_min // 10]
    d3 = tm.digit_to_segment[t.tm_min % 10]
    d4 = tm.digit_to_segment[t.tm_sec // 10]
    d5 = tm.digit_to_segment[t.tm_sec % 10]
    tm.set_segments([d0, 0x80 + d1, d2, 0x80 + d3, d4, d5])
    sleep(.2)
    tm.set_segments([d0, d1, d2, d3, d4, d5])

def speed_ui(tm):
    rospy.init_node('speed_ui', anonymous=True)
    r = rospy.Rate(10) # 10hz
    
    while not rospy.is_shutdown():
        r.sleep()
        # show_ip_address(tm)
        show_clock(tm)

if __name__ == "__main__":
    tm = TM1637(CLK, DIO)
    try:
        speed_ui(tm)
    except rospy.ROSInterruptException: pass
