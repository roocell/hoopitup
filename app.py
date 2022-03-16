import time
import board
import neopixel
import neo7seg
import neobox
import asyncio
import sys
import RPi.GPIO as GPIO
import mpu6050 as mpu
import audio
from logger import log as log


class app_data:
    def __init__(self):
        self.switch = 13 # GPIO13
        self.mode_button = 17 # GPIO17

        self.mpu_time = 0.1 # 100ms
        self.mpu_samples = 0
        self.motion = sys.maxsize # instantaneous motion
        self.motion_avg = 0 # averag motion
        self.motion_acc = 0 # accumulator for avg
        self.motion_settling_time = 3 # seconds

        self.last_switch_time = 0

appd = app_data()

# while True:
#
#     message = "01234567890abcdefghijklmnopqrstuvwxyz"
#     #neo7seg.message(pixels, offset, message, green, 1)
#     #neo7seg.message(pixels, offset, message, green, 1)
#     neo7seg.set(pixels, offset1, "1", green)
#     neo7seg.set(pixels, offset2, "2", red)
#     time.sleep(1)
#     neo7seg.set(pixels, offset1, "2", green)
#     neo7seg.set(pixels, offset2, "3", red)
#     time.sleep(1)
#     neo7seg.set(pixels, offset1, "3", green)
#     neo7seg.set(pixels, offset2, "1", red)
#     time.sleep(1)
#
#
#     log.debug("switch {}".format(switch.value))

class Timer:
    def __init__(self, timeout, callback, repeat):
        self._timeout = timeout
        self._callback = callback
        self._repeat = repeat
        self._task = asyncio.ensure_future(self._job())

    async def _job(self):
        await asyncio.sleep(self._timeout)
        await self._callback(self._repeat, self._timeout)

    def cancel(self):
        self._task.cancel()

def rim_moved():
    log.debug("rim_moved time {}".format(time.monotonic()))

def rim_done_moving(repeat, timeout):
    delta = time.monotonic() - appd.last_switch_time
    log.debug("rim_done_moving: last switch was {} sec ago".format(delta))
    # determine if shot was a miss or make
    if delta <= appd.motion_settling_time:
        # shot went in within our settleing time - it's a basket
        log.debug("made basket")
    else:
        log.debug("missed basket")


async def mpu_timer(repeat, timeout):
    # save power reading raw values
    acc_x = mpu.read_raw_data(mpu.ACCEL_XOUT_H)
    acc_y = mpu.read_raw_data(mpu.ACCEL_YOUT_H)
    acc_z = mpu.read_raw_data(mpu.ACCEL_ZOUT_H)
    gyro_x = mpu.read_raw_data(mpu.GYRO_XOUT_H)
    gyro_y = mpu.read_raw_data(mpu.GYRO_YOUT_H)
    gyro_z = mpu.read_raw_data(mpu.GYRO_ZOUT_H)
    appd.mpu_samples += 1
    # log.debug("acc_x {}\t acc_y {}\t acc_z {}\t gyro_x {}\t gyro_y {}\t gyro_z {}".format(
    #     acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z
    # ))

    # if values change by certain percentage, then decalre basket moved
    # but need to detect a change from stable state, then wait
    rising_edge_per = 800 # if more than this, the basket has received a jolt
    falling_edge_per = 5 # if less than this, the basket is settling down

    motion = (abs(gyro_x) + abs(gyro_y) + abs(gyro_z))
    appd.motion_acc += motion
    appd.mpu_samples += 1

    # TODO: will need something smarter than this after experimenting on real hoop
    movement_detected = False
    if motion > (appd.motion * rising_edge_per / 100):
        movement_detected = True
        rim_moved()
    appd.motion = motion

    if repeat:
        # easy debounce - don't look at MPU again until after settling time
        if movement_detected:
            donetimer = Timer(appd.motion_settling_time, rim_done_moving, False)
            Timer(appd.motion_settling_time, mpu_timer, True)
        else:
            Timer(appd.mpu_time, mpu_timer, True)

def switch_event(channel):
    # time.sleep(0.1) # need a delay if you want to read the value properly
    log.debug("switch triggered {} val:{}".format(channel, GPIO.input(channel)))
    appd.switch_last_time = time.monotonic()

async def fire_trail():
    await asyncio.sleep(0.5)
    appd.neobox.fire_trail(0.25, 2)
async def play_sound():
    appd.audio.playScoreSound()
    await asyncio.sleep(1)

async def mode_button_event_async(channel):
    log.debug("mode button triggered {} val:{}".format(channel, GPIO.input(channel)))
    await asyncio.gather(fire_trail(), play_sound())
    # appd.neobox.red_box(2)

def mode_button_event(channel):
    asyncio.run(mode_button_event_async(channel))


if __name__ == '__main__':

    # Choose an open pin connected to the Data In of the NeoPixel strip, i.e. board.D18
    # NeoPixels must be connected to D10, D12, D18 or D21 to work.
    pixel_pin = board.D12

    # The order of the pixel colors - RGB or GRB. Some NeoPixels have red and green reversed!
    # For RGBW NeoPixels, simply change the ORDER to RGBW or GRBW.
    ORDER = neopixel.GRB
    num_pixels = neo7seg.getNumPixels()*2 + neobox.get_num_pixels()
    pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.5, auto_write=False, pixel_order=ORDER)

    green = (0, 255, 0)
    red = (255, 0, 0)
    offset1 = 0
    offset2 = neo7seg.getNumPixels()

    # neobox is after the 7seg's
    appd.neobox = neobox.NeoBox(pixels, neo7seg.getNumPixels()*2)

    # init Audio
    appd.audio = audio.Audio()

    # setup the GPIO (neopixel alreayd sets BCM mode)
    log.debug("mode {}".format(GPIO.getmode()))
    GPIO.setwarnings(True)
    GPIO.setup(appd.switch, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(appd.switch, GPIO.FALLING, callback=switch_event, bouncetime=200)

    GPIO.setup(appd.mode_button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(appd.mode_button, GPIO.FALLING, callback=mode_button_event, bouncetime=500)

    # don't have 6 pins to rim box so can't take advantage of MPU6050 INT pin.
    # (who knows...the INT pin might not have been sufficient anyways)
    # have to use an asynio timer instead to read MPY6050
    mpu.MPU_Init()
    timer = Timer(appd.mpu_time, mpu_timer, True)

    # run the event loop
    appd.loop = asyncio.get_event_loop()
    appd.loop.run_forever()
    appd.loop.close()

    # cleanup
    GPIO.cleanup()
