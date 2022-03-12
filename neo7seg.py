#!/usr/bin/env python3
# 7 segment neopixel display
# This is meant to be just a part of a neopixel chain
# The entire neopixel chain needs to be instantiated outside of this file
# and then passed in with an offset
import time
import board
import neopixel

pix_per_seg = 4
def getNumPixels():
    return pix_per_seg*7


# the 7 seg is a series of 7 (4 pixel) segments
# the order of segments is as follow
# described using an index 0..6
#   5 5 5 5
#  4       0
#  4       0
#  4       0
#  4       0
#   6 6 6 6
#  3       1
#  3       1
#  3       1
#  3       1
#   2 2 2 2
# we can define characters as an array of segment indicies
# order of indicies doesn't matter
lookup = {} # dict to use string as index
lookup['0'] = [0,1,2,3,4,5]
lookup['1'] = [0,1]
lookup['2'] = [5,0,6,3,2]
lookup['3'] = [5,0,6,1,2]
lookup['4'] = [4,6,0,1]
lookup['5'] = [5,4,6,1,2]
lookup['6'] = [5,4,6,1,2,3]
lookup['7'] = [5,0,1]
lookup['8'] = [0,1,2,3,4,5,6]
lookup['9'] = [4,5,6,0,1,2]
lookup['A'] = lookup['a'] = [3,1,6,4,5,0]
lookup['B'] = lookup['b'] = [1,2,3,4,6]
lookup['C'] = lookup['c'] = [5,4,3,2]
lookup['D'] = lookup['d'] = [0,1,2,3,6]
lookup['E'] = lookup['e'] = [5,4,6,3,2]
lookup['F'] = lookup['f'] = [5,4,6,3]
lookup['G'] = lookup['g'] = [5,4,1,2,3]
lookup['H'] = lookup['h'] = [4,3,6,1]
lookup['I'] = lookup['i'] = [1]
lookup['J'] = lookup['j'] = [0,1,2,3]
lookup['K'] = lookup['k'] = [3,1,6,4,5]
lookup['L'] = lookup['l'] = [4,3,2]
lookup['M'] = lookup['m'] = [3,6,1,5]
lookup['N'] = lookup['n'] = [3,6,1]
lookup['O'] = lookup['o'] = [1,2,3,6]
lookup['P'] = lookup['p'] = [3,4,5,0,6]
lookup['Q'] = lookup['q'] = [6,4,5,0,1]
lookup['R'] = lookup['r'] = [3,6]
lookup['S'] = lookup['s'] = [5,4,6,1,2]
lookup['T'] = lookup['t'] = [4,6,3,2]
lookup['U'] = lookup['u'] = [4,3,2,1,0]
lookup['V'] = lookup['v'] = [1,2,3]
lookup['W'] = lookup['w'] = [4,6,0,2]
lookup['X'] = lookup['x'] = [4,6,0,3,1]
lookup['Y'] = lookup['y'] = [4,6,0,1,2]
lookup['Z'] = lookup['z'] = [5,0,6,3,2]

def clear(pixels, offset):
    for s in range(7):
        for p in range (0, pix_per_seg):
            pixels[offset + s*pix_per_seg + p] = (0,0,0)


# pixels = neopixels instantiated outside this function
# offset = the offset for the first pixel in 7seg in the entire neopixel chain
# value = character to display
# colour = (r,b,g)
def set(pixels, offset, value, colour):
    # since we're just part of a neopixel chain - we should only clear
    # what's in our 7seg
    clear(pixels, offset)
    character = lookup[value]
    for s in character:
        for p in range (0, pix_per_seg):
            pixels[offset + s*pix_per_seg + p] = colour
    pixels.show()

def message(pixels, offset, message, colour, wait):
    for i in range(0, len(message)):
        set(pixels, offset, message[i], colour)
        time.sleep(wait)
