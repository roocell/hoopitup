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

### DEFINES ############################
green =     (0,   255, 0)
red =       (255, 0,   0)
blue =      (0,   98,  255)
yellow =    (255, 221, 0)
black =     (0,   0,   0)
purple =    (238, 0,   255)

print_motion_data = False

############ GLOBAL APPDATA ##################
class app_data:
    def __init__(self):
        self.switch = 13 # GPIO13
        self.mode_button = 17 # GPIO17

        self.mpu_time = 0.025 # 25 ms
        self.mpu_samples = 0
        self.num_samples_for_avg = 4
        self.motion_acc = 0 # accumulator for avg
        self.motion_limit = 115 # % of stable (last reading to declare motion)

        self.motion = sys.maxsize # instantaneous motion
        self.motion_settling_time = 2 # seconds to determine miss
        self.motion_settling_time_race = 0.5 # to prevent race condition
        self.modetimer = None
        self.last_switch_time = 0

        # game config
        self.game_is_starting_up = False # need this so a reset can't be done during starup sequence
        self.game_started = False # need this so we dont count shots/misses before the game starts
        # shootout game config
        # makes on top of box
        # misses on bottom of box
        self.shootout_timer = None
        self.makes = 0
        self.misses = 0
        self.countdown = 0
        self.shootout_neobox_offset_make = 20
        self.shootout_neobox_offset_miss = 50
        self.shootout_countdown_sec = 60


appd = app_data()


################ TIMER CLASS ################
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


##################### MOTION #############################
def rim_moved(current, last, change_per):
    log.debug("rim_moved time %.1f current %d last %d change_per %2.1f",
        time.monotonic(),
        current, last, change_per)

async def rim_done_moving(repeat, timeout):
    delta = time.monotonic() - appd.last_switch_time
    log.debug("rim_done_moving: last switch was {} sec ago".format(delta))
    # determine if shot was a miss or make
    if delta <= (appd.motion_settling_time + appd.motion_settling_time_race):
        # shot went in within our settleing time - it's a basket
        log.debug("made basket")
    else:
        log.debug("missed basket")
        await game_mode_process_miss()

async def mpu_timer(repeat, timeout):
    # sometimes we may get a bus error which results in an exception
    # we need to ignore this and continue taking samples
    try:
        # save power reading raw values
        acc_x = mpu.read_raw_data(mpu.ACCEL_XOUT_H)
        acc_y = mpu.read_raw_data(mpu.ACCEL_YOUT_H)
        acc_z = mpu.read_raw_data(mpu.ACCEL_ZOUT_H)
        gyro_x = mpu.read_raw_data(mpu.GYRO_XOUT_H)
        gyro_y = mpu.read_raw_data(mpu.GYRO_YOUT_H)
        gyro_z = mpu.read_raw_data(mpu.GYRO_ZOUT_H)
    except Exception as e:
        log.error(">>>>Error>>>> {} ".format(e))
        Timer(appd.mpu_time, mpu_timer, True)
        return

    # if values change by certain percentage, then decalre basket moved
    # but need to detect a change from stable state, then wait

    #motion = (abs(gyro_x) + abs(gyro_y) + abs(gyro_z))
    motion = (abs(acc_x) + abs(acc_y) + abs(acc_z))
    appd.motion_acc += motion
    appd.mpu_samples += 1

    if appd.mpu_samples % appd.num_samples_for_avg == 0:
        motion = appd.motion_acc / appd.num_samples_for_avg
        appd.motion_acc = 0
    else:
        # take more samples before evaluating
        Timer(appd.mpu_time, mpu_timer, True)
        return

    # TODO: will need something smarter than this after experimenting on real hoop
    movement_detected = False
    if motion > (appd.motion * appd.motion_limit / 100):
        movement_detected = True
        rim_moved(motion, appd.motion, (motion * 100 / appd.motion))

    if print_motion_data == True:
        change_per = (motion * 100 / appd.motion)
        log.debug("ax %4d\t ay %6d\t az %3d\t gx %4d\t gy %4d\t gz %4d\t "
            "m %d\t appd.m %d per %2.1f",
            acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, motion, appd.motion, change_per
        )
    appd.motion = motion


    if repeat:
        if movement_detected:
            donetimer = Timer(appd.motion_settling_time, rim_done_moving, False)
            # easy debounce - don't look at MPU again until after settling time
            Timer(appd.motion_settling_time, mpu_timer, True)
        else:
            Timer(appd.mpu_time, mpu_timer, True)

################ GAME MODES #####################################
# to change modes, hold mode button for 3 secs
# push mode button to reset current mode
GAME_MODE_SHOOTOUT = "SH"
GAME_MODE_SHOT_COUNT = "SC"

game_modes = (
    GAME_MODE_SHOOTOUT,
    GAME_MODE_SHOT_COUNT,
    )

# SH - 60sec shootout
#      3(beep),2(beep),1(beep), (BEEEEEEP)
#      7segs countdown, neobox counts makes(top)/misses(bottom)
#      (optionally count down on neobox and count shots on 7seg)
#      buzzer at end, then display shot %
# SC - shot counter
#      no time limit, counts makes on 7seg, plays score/miss sounds and animates neobox
# VS - vs mode
#     ???
async def shootout_display_per(repeat, timeout):
    per = 0
    if (appd.makes + appd.misses) > 0:
        per = appd.makes*100/(appd.makes + appd.misses)
    appd.neo7seg.set(per, purple)

async def shootout_timer(repeat, timeout):
    appd.countdown -= 1
    if appd.countdown > 5:
        appd.neo7seg.set(appd.countdown, green)
        appd.shootout_timer = Timer(1, shootout_timer, True)
    elif appd.countdown >= 1:
        appd.neo7seg.set(appd.countdown, yellow)
        appd.shootout_timer = Timer(1, shootout_timer, True)
        await appd.audio.play_beep1()
    else:
        # done!
        appd.neo7seg.set(appd.countdown, red)
        log.debug("shootout over!")
        await appd.audio.play_buzzer()
        Timer(2, shootout_display_per, False)

async def start_game_mode_shootout():
    appd.game_is_starting_up = True
    appd.game_started = False
    appd.makes = 0
    appd.misses = 0
    appd.shootout_make_and_misses = [black for i in range(100)]
    appd.neobox.clear()

    if isinstance(appd.shootout_timer, Timer):
        appd.shootout_timer.cancel()

    # GAME_MODE_SHOOTOUT we need a 3 sec countdown with beeps
    appd.neo7seg.set("3", blue)
    await appd.audio.play_beep1()
    await asyncio.sleep(1)
    appd.neo7seg.set("2", blue)
    await appd.audio.play_beep1()
    await asyncio.sleep(1)
    appd.neo7seg.set("1", blue)
    await appd.audio.play_beep1()
    await asyncio.sleep(1)
    appd.neo7seg.set("GO")
    await appd.audio.play_beep2()
    await asyncio.sleep(1)
    appd.countdown = appd.shootout_countdown_sec
    appd.neo7seg.set(appd.countdown)
    appd.shootout_timer = Timer(1, shootout_timer, True)
    appd.game_started = True
    appd.game_is_starting_up = False

async def game_mode_process_make():
    if appd.game_started == False:
        log.debug("ignoring make")
        return
    appd.makes += 1
    if appd.game_mode == GAME_MODE_SHOT_COUNT:
        # gather these two asynchronous functions so they run concurrently
        # defining the other functions as async and using "await asyncio.sleep()"
        # inside them, allow the mpu async timer to also run concurrently
        appd.neo7seg.set(appd.makes, red)
        await asyncio.gather(appd.neobox.fire_trail(0.25, 2), appd.audio.play_scored_sound(), appd.neo7seg.rainbow_digits(3))
    elif appd.game_mode == GAME_MODE_SHOOTOUT:
        # count makes/misses on neobox
        log.debug("shootout make {}".format(appd.makes))
        appd.shootout_make_and_misses[appd.shootout_neobox_offset_make + appd.makes] = green
        appd.neobox.set(appd.shootout_make_and_misses)

async def game_mode_process_miss():
    if appd.game_started == False:
        log.debug("ignoring miss")
        return
    appd.misses += 1
    if appd.game_mode == GAME_MODE_SHOT_COUNT:
        await asyncio.gather(appd.audio.play_missed_sound(), appd.neobox.red_box(2))

    elif appd.game_mode == GAME_MODE_SHOOTOUT:
        log.debug("shootout miss {}".format(appd.misses))
        appd.shootout_make_and_misses[appd.shootout_neobox_offset_miss + appd.misses] = red
        appd.neobox.set(appd.shootout_make_and_misses)

async def start_game_mode_shotcount():
    appd.makes = 0
    appd.neo7seg.set(appd.makes)
    appd.game_is_starting_up = False
    appd.game_started = True

game_start_funcs = {}
game_start_funcs[GAME_MODE_SHOOTOUT] = start_game_mode_shootout
game_start_funcs[GAME_MODE_SHOT_COUNT] = start_game_mode_shotcount

##########   MODE BUTTON ##################
async def mode_detect(repeat, timeout):
    log.debug("game mode change")
    for m in range(len(game_modes)):
        if game_modes[m] == appd.game_mode:
            if m < (len(game_modes) - 1):
                appd.game_mode = game_modes[m + 1]
            else:
                appd.game_mode = game_modes[0]
            break
    log.debug("changed to mode {}".format(appd.game_mode))
    appd.neo7seg.set(appd.game_mode, blue)
    time.sleep(1)
    # button up will trigger reset and start game
    #await game_start_funcs[appd.game_mode]()

async def mode_button_event_async_exp(channel):
    log.debug("mode triggered {} val: {}".format(channel, GPIO.input(channel)))
    if isinstance(appd.modetimer, Timer):
        appd.modetimer.cancel()
    if GPIO.input(channel) == True:
        # if rising edge - reset current mode
        log.debug("resetting")
        appd.neo7seg.set("--")
        time.sleep(1)
        await game_start_funcs[appd.game_mode]()
    else:
        # possible holding for mode reset
        appd.modetimer = Timer(3, mode_detect, False)

async def mode_button_event_async(channel):
    # https://www.joeltok.com/blog/2020-10/python-asyncio-create-task-fails-silently
    # any syntax error inside our coroutine will fail silently.
    # we have to explicitly raise any exceptions here
    try:
        await mode_button_event_async_exp(channel)
    except Exception as e: log.error(">>>>Error>>>> {} ".format(e))

def mode_button_event(channel):
    if appd.game_started == False and appd.game_is_starting_up == True:
        log.debug("ignoring mode button")
        return
    return asyncio.run_coroutine_threadsafe(mode_button_event_async(channel), appd.loop)

def game_mode_init():
    log.debug("setting gamemode {}".format(GAME_MODE_SHOOTOUT))
    log.debug("hit reset to start")
    appd.game_mode = GAME_MODE_SHOT_COUNT
    # require reset button to start
    appd.neo7seg.set(appd.game_mode, blue)

################  BASKET SWITCH #############################
async def switch_event_async(channel):
    # https://www.joeltok.com/blog/2020-10/python-asyncio-create-task-fails-silently
    # any syntax error inside our coroutine will fail silently.
    # we have to explicitly raise any exceptions here
    try:
        await game_mode_process_make()
    except Exception as e: log.error(">>>>Error>>>> {} ".format(e))

def switch_event(channel):
    #time.sleep(0.1) # need a delay if you want to read the value properly
    appd.last_switch_time = time.monotonic()
    log.debug("switch triggered {} val: {} time: {}".format(channel, GPIO.input(channel), appd.last_switch_time))
    # GPIO event is not on mainthread so we have to store the main event loop in appd
    # and then use it here
    asyncio.run_coroutine_threadsafe(switch_event_async(channel), appd.loop)



######################## MAIN ##########################
if __name__ == '__main__':

    # Choose an open pin connected to the Data In of the NeoPixel strip, i.e. board.D18
    # NeoPixels must be connected to D10, D12, D18 or D21 to work.
    pixel_pin = board.D12

    # The order of the pixel colors - RGB or GRB. Some NeoPixels have red and green reversed!
    # For RGBW NeoPixels, simply change the ORDER to RGBW or GRBW.
    ORDER = neopixel.GRB
    num_pixels = neo7seg.get_num_pixels(2) + neobox.get_num_pixels()
    pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.5, auto_write=False, pixel_order=ORDER)

    # display some init message
    appd.neo7seg = neo7seg.Neo7Seg(pixels, 0, 2)
    appd.neo7seg.set("ST")

    # neobox is after the 7seg's
    appd.neobox = neobox.NeoBox(pixels, neo7seg.get_num_pixels(2))
    #appd.neobox.set([red for i in range(5)])

    # init Audio
    appd.audio = audio.Audio()

    # setup the GPIO (neopixel alreayd sets BCM mode)
    GPIO.setwarnings(True)
    GPIO.setup(appd.switch, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(appd.switch, GPIO.FALLING, callback=switch_event, bouncetime=1000)

    GPIO.setup(appd.mode_button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(appd.mode_button, GPIO.BOTH, callback=mode_button_event, bouncetime=50)

    # don't have 6 pins to rim box so can't take advantage of MPU6050 INT pin.
    # (who knows...the INT pin might not have been sufficient anyways)
    # have to use an asynio timer instead to read MPY6050
    mpu.MPU_Init()
    timer = Timer(appd.mpu_time, mpu_timer, True)

    game_mode_init()

    # run the event loop
    appd.loop = asyncio.get_event_loop()
    appd.loop.run_forever()
    appd.loop.close()

    # cleanup
    GPIO.cleanup()
