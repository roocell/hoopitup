import time
import board
import neopixel
import neo7seg

# Choose an open pin connected to the Data In of the NeoPixel strip, i.e. board.D18
# NeoPixels must be connected to D10, D12, D18 or D21 to work.
pixel_pin = board.D12


# The order of the pixel colors - RGB or GRB. Some NeoPixels have red and green reversed!
# For RGBW NeoPixels, simply change the ORDER to RGBW or GRBW.
ORDER = neopixel.GRB
num_pixels = neo7seg.getNumPixels()*2
pixels = neopixel.NeoPixel(
    pixel_pin, num_pixels, brightness=0.5, auto_write=False, pixel_order=ORDER
)

green = (0, 255, 0)
red = (255, 0, 0)
offset1 = 0
offset2 = neo7seg.getNumPixels()
while True:
    message = "01234567890abcdefghijklmnopqrstuvwxyz"
    #neo7seg.message(pixels, offset, message, green, 1)
    #neo7seg.message(pixels, offset, message, green, 1)
    neo7seg.set(pixels, offset1, "1", green)
    neo7seg.set(pixels, offset2, "2", red)
    time.sleep(1)
    neo7seg.set(pixels, offset1, "2", green)
    neo7seg.set(pixels, offset2, "3", red)
    time.sleep(1)
    neo7seg.set(pixels, offset1, "3", green)
    neo7seg.set(pixels, offset2, "1", red)
    time.sleep(1)
