# hoopitup
raspberry pi project. add-on to driveway basketball hoop

https://learn.adafruit.com/adafruit-neopixel-uberguide/best-practices
https://learn.adafruit.com/neopixels-on-raspberry-pi/raspberry-pi-wiring


anker powercore 20100: 20100 mAh / 72.36 wh ; Output : 5V / 4.8A
4.8A can power ~50 neopixels

https://www.amazon.ca/38800mAh-Display-Portable-Charging-Compatible/dp/B09PZV62V3/ref=sr_1_5?crid=1TBF57JE1DSEF&keywords=power+bank&qid=1646747404&sprefix=powerbank%2Caps%2C243&sr=8-5
4 2.1A USB ports: 1 for raspi, 3 other for combined 6.3A (70 neopixels)

https://www.digikey.ca/en/products/detail/sparkfun-electronics/COM-08530/5684342
this 7 segment display is interesting (would need a 8bit shift register for each as well).
But we can also use neopixels if we make custom plastic like here (arguably cheaper and simpler design)
https://learn.adafruit.com/ninja-timer-giant-7-segment-display/overview
https://www.amazon.ca/gp/product/B08JGP969X/ref=crt_ewc_img_dp_1?ie=UTF8&smid=A3DWYIK6Y9EEQB&th=1
https://www.amazon.ca/gp/product/B07XCND8ZJ/ref=crt_ewc_img_dp_4?ie=UTF8&psc=1&smid=A2PFIQQO7UBV3G


custom 7 segment Display
4 neopixels per segment.
need a little 3" x 0.75" box to encase a segment.
print out digit on sticker https://www.amazon.ca/gp/product/B07XCND8ZJ/ref=ox_sc_act_image_1?smid=A2PFIQQO7UBV3G&psc=1
translucent white outer box

pizero sound w/ externally power 3.5mm speaker
https://www.digikey.ca/en/products/detail/adafruit-industries-llc/4037/9770512
https://www.ihomeaudio.com/ibt72pc/

Keystudio Mic Hat (similar to Adafruit's) https://wiki.keyestudio.com/Ks0314_keyestudio_ReSpeaker_2-Mic_Pi_HAT_V1.0
- this doesn't have GPIO extensions so I'll have to mount to another PCB
- might have to power everything through this daughter board
  (not sure - had to run the install twice - seems to work powered via pi now)
```
git clone https://github.com/respeaker/seeed-voicecard.git
cd seeed-voicecard/
sudo ./install.sh
(this will update kernel, etc)
sudo raspi-config  (enable SPI interface by default) (for LEDs)
sudo apt-get install mpg123
cd hoopitup
mpg123 audio/kaboom-5.mp3
```

neopixles need GPIO  10,12,18,21 to work
audio hat uses
 - 12,21 for I2S (digital audio)
 - GPIO10 for SPI_MOSI (for LEDs) - so could use this
 - GPIO12 for a grove connector (which we're not using) - so could use this.