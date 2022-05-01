#!/usr/bin/python3
import time
import board
import neopixel
import neo7seg
import neobox
import asyncio
import sys
import RPi.GPIO as GPIO
import audio
import timer
import motion
from logger import log as log

### DEFINES ############################
green =     (0,   255, 0)
red =       (255, 0,   0)
blue =      (0,   98,  255)
yellow =    (255, 221, 0)
black =     (0,   0,   0)
purple =    (238, 0,   255)


############ GLOBAL APPDATA ##################
class app_data:
    def __init__(self):
        self.switch = 13 # GPIO13
        self.mode_button = 17 # GPIO17

        self.modetimer = None
        self.last_switch_time = 0

        self.motion = None

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

############### MOTION ###########
async def rim_done_moving(repeat, timeout):
    settling_time = (appd.motion.motion_settling_time + appd.motion.motion_settling_time_race)
    delta = time.monotonic() - appd.last_switch_time
    log.debug("rim_done_moving: last switch was {} sec ago".format(delta))
    # determine if shot was a miss or make
    if delta <= settling_time:
        # shot went in within our settleing time - it's a basket
        log.debug("made basket")
    else:
        log.debug("missed basket")
        await game_mode_process_miss()



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
        appd.shootout_timer = timer.Timer(1, shootout_timer, True)
    elif appd.countdown >= 1:
        appd.neo7seg.set(appd.countdown, yellow)
        appd.shootout_timer = timer.Timer(1, shootout_timer, True)
        await appd.audio.play_beep1()
    else:
        # done!
        appd.neo7seg.set(appd.countdown, red)
        log.debug("shootout over!")
        await appd.audio.play_buzzer()
        timer.Timer(2, shootout_display_per, False)

async def start_game_mode_shootout():
    appd.game_is_starting_up = True
    appd.game_started = False
    appd.makes = 0
    appd.misses = 0
    appd.shootout_make_and_misses = [black for i in range(100)]
    appd.neobox.clear()

    if isinstance(appd.shootout_timer, timer.Timer):
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
    appd.shootout_timer = timer.Timer(1, shootout_timer, True)
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
        await asyncio.gather(appd.neobox.fire_trail(0.25, 1), appd.audio.play_scored_sound(), appd.neo7seg.rainbow_digits(3))
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
    if isinstance(appd.shootout_timer, timer.Timer):
        appd.shootout_timer.cancel()
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
    await appd.audio.play_beep2()
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
    if isinstance(appd.modetimer, timer.Timer):
        appd.modetimer.cancel()
    if GPIO.input(channel) == True:
        # if rising edge - reset current mode
        log.debug("resetting")
        appd.neo7seg.set("--")
        await appd.audio.play_beep1()
        time.sleep(1)
        await game_start_funcs[appd.game_mode]()
    else:
        # possible holding for mode reset
        appd.modetimer = timer.Timer(3, mode_detect, False)

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
    GPIO.add_event_detect(appd.switch, GPIO.FALLING, callback=switch_event, bouncetime=2000)

    GPIO.setup(appd.mode_button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(appd.mode_button, GPIO.BOTH, callback=mode_button_event, bouncetime=50)

    try:
        appd.motion = motion.Motion(rim_done_moving)
    except Exception as e:
        # if the motion box isn't connected (or broken) we'll get here
        log.error(">>>>Motion Module Error>>>> {} ".format(e))
        appd.audio.play_sound(audio.buzzer)


    game_mode_init()

    # run the event loop
    appd.loop = asyncio.get_event_loop()
    appd.loop.run_forever()
    appd.loop.close()

    # cleanup
    GPIO.cleanup()
