#  sudo apt-get install python3-smbus

# Lidar
# https://learn.adafruit.com/circuitpython-on-raspberrypi-linux/installing-circuitpython-on-raspberry-pi
# https://learn.adafruit.com/adafruit-vl53l0x-micro-lidar-distance-sensor-breakout/python-circuitpython
# pip3 install Adafruit-Blinka --upgrade
# sudo pip3 install adafruit-circuitpython-vl53l0x
#
# https://www.st.com/resource/en/datasheet/vl53l0x.pdf
# https://www.st.com/resource/en/user_manual/um2039-world-smallest-timeofflight-ranging-and-gesture-detection-sensor-application-programming-interface-stmicroelectronics.pdf
# https://github.com/pimoroni/VL53L0X-python/blob/master/python/VL53L0X.py
# https://github.com/GrimbiXcode/VL53L0X-Register-Map
# https://github.com/adafruit/Adafruit_CircuitPython_VL53L0X

# Hoop diameter is 18"
# kids ball is 25.5" in circumference (~8.12" diameter)
# adult ball is 29.5" in circumference (~9.39" diameter)
# So an adult will ALWAYS cross the centre, but a kids ball
# (although unlikely) has a chance to miss the beam.
# however, our lidar beam isn't right at rim height. it's lower and
# the ball will be gathered by the mesh more towards the center.
# considering this, a single beam should catch the ball fine.
import time
import board
import busio
import adafruit_vl53l0x
import timer
from logger import log as log
import asyncio

class Lidar:
    def __init__(self, callback):
        self.time = 0.025 # 25 ms
        self.threshold = 305 # mm (12")
        self.callback = callback
        self.last_reading = 9999
        self.debounce = 1 # second

        # Initialize I2C bus and sensor.
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.vl53 = adafruit_vl53l0x.VL53L0X(self.i2c)

        timer.Timer(self.time, self.vl53_timer, True)


        # fastest it can go is 20ms
        # you lose accuracy when it's faster - but we dont care.
        self.vl53.measurement_timing_budget = 20000

        #self.configure_interrupt(350)

    async def vl53_timer(self, repeat, timeout):
        # sometimes we may get a bus error which results in an exception
        # we need to ignore this and continue taking samples
        try:
            r = self.vl53.range
            #log.debug(r)
            if r < self.threshold and self.last_reading > self.threshold:
                log.debug("low threshold triggered {}".format(r))
                await self.callback(True)
                timer.Timer(self.debounce, self.vl53_timer, True)
                self.last_reading = r
                return
            self.last_reading = r
        except Exception as e:
            log.error(">>>>Error>>>> {} ".format(e))

        timer.Timer(self.time, self.vl53_timer, True)


    # the adafruit python code doesn't have any interrupt support
    # so we'll do it here
    # def clear_interrupt(self):
    #     self.vl53._write_u8(adafruit_vl53l0x._SYSTEM_INTERRUPT_CLEAR, 0x01)
    #
    # def configure_interrupt(self, mm):
    #     #with self.vl53.continuous_mode():
    #     self.vl53.start_continuous() # need this mode for interrupt
    #
    #     # set distance to trigger
    #     self.vl53._write_u8(adafruit_vl53l0x._SYSTEM_THRESH_LOW, mm>>1)
    #
    #     # set low distance trigger mode
    #     # 0x00: Disabled
    #     # 0x01: Low level
    #     # 0x02: High level
    #     # 0x03: Out of window
    #     # 0x04: New sample ready
    #     self.vl53._write_u8(adafruit_vl53l0x._SYSTEM_INTERRUPT_CONFIG_GPIO, 0x02)
    #
    #     self.clear_interrupt()


# Optionally adjust the measurement timing budget to change speed and accuracy.
# See the example here for more details:
#   https://github.com/pololu/vl53l0x-arduino/blob/master/examples/Single/Single.ino
# For example a higher speed but less accurate timing budget of 20ms:
# vl53.measurement_timing_budget = 20000
# Or a slower but more accurate timing budget of 200ms:
# vl53.measurement_timing_budget = 200000
# The default timing budget is 33ms, a good compromise of speed and accuracy.

if __name__ == '__main__':
    vl53 = Lidar()
    # Main loop will read the range and print it every second.

    # with vl53.vl53.continuous_mode():
    #     while True:
    #         # try to adjust the sleep time (simulating program doing something else)
    #         # and see how fast the sensor returns the range
    #         time.sleep(0.1)
    #
    #         curTime = time.time()
    #         print("Range: {0}mm ({1:.2f}ms)".format(vl53.vl53.range, time.time() - curTime))

    while True:
        print("Range: {0}mm".format(vl53.vl53.range))
        time.sleep(1.0)
