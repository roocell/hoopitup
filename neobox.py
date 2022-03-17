# this file contains routines that will animate the neopixel box
import board
import neopixel
import asyncio
import sys
from logger import log as log

# tip: google "rgb color picker"

# need a global in order to init neopixels first before instantiating this class
num_pixels = 100
def get_num_pixels():
    return num_pixels;

class NeoBox:
    def __init__(self, pixels, offset):
        self._pixels = pixels
        self._offset = offset
        self._num_pixels = num_pixels
        self.clear()

    def clear(self):
        for p in range(self._num_pixels):
            self._pixels[self._offset+p] = (0,0,0)
        self._pixels.show()

    def set(self, color_arr):
        a = self._offset
        for c in color_arr:
            self._pixels[a] = c
            a += 1
        self._pixels.show()

    # this sends a trail of LEDs across the strip in the colour of fire
    async def fire_trail(self, duration, laps = 1):
        trail_len = 10
        colors = []
        for i in range(trail_len):
            colors.append((255,int(i*100/trail_len), 0))

        for l in range(laps):
            for p in range(self._num_pixels):
                if p >= trail_len:
                    self._pixels[self._offset+p-trail_len] = (0,0,0)
                if p < (self._num_pixels - trail_len):
                    for c in range(len(colors)):
                        self._pixels[self._offset+p+c] = colors[c]
                else:
                    self._pixels[self._offset+p] = (0,0,0)
                self._pixels.show()
                await asyncio.sleep(duration/self._num_pixels)

    async def red_box(self, timeout):
        red = (255, 0, 0)
        for p in range(self._num_pixels):
            self._pixels[self._offset+p] = red
        self._pixels.show()
        await asyncio.sleep(timeout)
        self.clear()
