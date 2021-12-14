# -*- coding: utf-8 -*-
from utility import *
from pydub import AudioSegment
log = logger(__name__)


class Song():
    def __init__(self, file, bpm):
        self.file = file
        self.org_sound = AudioSegment.from_ogg(file)
        self.sound = self.org_sound
        self.len = len(self.sound) # [msec]
        self.bpm        = bpm
        self.start      = None # [beat]
        self.end        = None # [beat]
        self.fadein     = None # [beat]
        self.fadeout    = None # [beat]
        self.xfade      = None # [sec]
        self.presilence = None # [sec]

    def Trimming(self):
        start = round45(beat2msec(self.start, self.bpm))
        end = round45(beat2msec(self.end, self.bpm))
        self.sound = self.sound[start:end]
        log.debug(f'音声トリミング: {msec2timestr(start)}-{msec2timestr(end)}')

    def fade(self):
        if self.fadein != 0:
            fadein = round45(beat2msec(self.fadein, self.bpm))
            self.sound = self.sound.fade_in(fadein)
            log.debug(f'フェードイン: {fadein/1000}sec')
        if self.fadeout != 0:
            fadeout = round45(beat2msec(self.fadeout, self.bpm))
            self.sound = self.sound.fade_out(fadeout)
            log.debug(f'フェードアウト: {fadeout/1000}sec')


# トリミング＆フェード処理
def EditSound(songlist):
    log.info('音声編集中...')
    for song in songlist:
        song.sound = song.org_sound
        song.Trimming()
        song.fade()
    log.info('音声編集完了')

# 音声結合
def ConcatenateSongs(songlist):
    log.info('音声結合中...')
    sounds = [song.sound for song in songlist]
    sound = sounds[0]
    for i in range(1,len(songlist)):
        sound = sound.append(sounds[i], songlist[i].xfade)
    log.info('音声結合完了')
    return sound

