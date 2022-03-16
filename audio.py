# sudo apt-get install vlc
# sudo pip3 install python-vlc
# to adjust audio: alsamixer

import vlc
import random
import asyncio
from logger import log as log

sounds = {}
sounds["boom-2"] = "boom-2.mp3"
sounds["boom-4"] = "boom-4.mp3"
sounds["bullseye"] = "bullseye.mp3"
sounds["embarassing"] = "embarassing.mp3"
sounds["empty"] = "empty.mp3"
sounds["get-out"] = "get-out.mp3"
sounds["heating-up"] = "heating-up.mp3"
sounds["hole"] = "hole.mp3"
sounds["kaboom"] = "kaboom-5.mp3"
sounds["long-range"] = "long-range.mp3"
sounds["love-it"] = "love-it.mp3"
sounds["no-good"] = "no-good.mp3"
sounds["no-mans-land"] = "no-mans-land.mp3"
sounds["not-close"] = "not-close.mp3"
sounds["on-fire"] = "on-fire.mp3"
sounds["ouch"] = "ouch.mp3"
sounds["party"] = "party.mp3"
sounds["rejected"] = "rejected.mp3"
sounds["too-easy"] = "too-easy.mp3"
sounds["ut-oh"] = "ut-oh.mp3"
sounds["wild-shot"] = "wild-shot.mp3"
sounds["yes"] = "yes.mp3"

score = (
    sounds["boom-2"],
    sounds["boom-4"],
    sounds["bullseye"],
    sounds["heating-up"],
    sounds["kaboom"],
    sounds["long-range"],
    sounds["love-it"],
    sounds["no-mans-land"],
    sounds["on-fire"],
    sounds["party"],
    sounds["too-easy"],
    sounds["yes"]
    )
miss = (
    sounds["embarassing"],
    sounds["empty"],
    sounds["no-good"],
    sounds["get-out"],
    sounds["not-close"],
    sounds["ouch"],
    sounds["rejected"],
    sounds["ut-oh"],
    sounds["wild-shot"]
    )


class Audio:
    def __init__(self):
        self._score_audio = []
        for s in score:
            self._score_audio.append(vlc.MediaPlayer("audio/"+s))

    def playScoreSound(self):
        r = random.randrange(0, len(self._score_audio), 1)
        log.debug("playing {}".format(score[r]))
        self._score_audio[r].play()
