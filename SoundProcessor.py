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
        self.speed      = 1    # scale
        self.start      = None # [beat]
        self.end        = None # [beat]
        self.fadein     = None # [beat]
        self.fadeout    = None # [beat]
        self.xfade      = 0    # [beat]
        self.silence    = None # [beat]
        self.postXfade  = 0    # [beat]

    def Trimming(self):
        start = round45(beat2msec(self.start, self.bpm))
        end = round45(beat2msec(self.end, self.bpm))
        self.sound = self.sound[start:end]
        log.debug(f'音声トリミング: {msec2timestr(start)}-{msec2timestr(end)}')

    def fade(self):
        if (fadeinDuration := beat2msec(self.fadein, self.bpm)) > 0:
            self.sound = self.sound.fade_in(round45(fadeinDuration))
            log.debug(f'フェードイン: {round45(fadeinDuration)/1000}sec')
        if (fadeoutDuration := beat2msec(self.fadeout, self.bpm)) > 0:
            self.sound = self.sound.fade_out(round45(fadeoutDuration))
            log.debug(f'フェードアウト: {round45(fadeoutDuration)/1000}sec')

    def AddSilence(self):
        if (silenceDuration := beat2msec(self.silence, self.bpm)) < 0:
            silence = AudioSegment.silent(round45(-silenceDuration))
            self.sound = silence.append(self.sound, crossfade=0)
            log.debug(f'*start前の無音区間: {round45(silenceDuration)/1000}sec')
        if (silenceDuration := beat2msec(self.silence, self.bpm)) > 0:
            silence = AudioSegment.silent(round45(silenceDuration))
            self.sound = self.sound.append(silence, crossfade=0)
            log.debug(f'*end後の無音区間: {round45(silenceDuration)/1000}sec')
        self.len = len(self.sound)

    # 保留
    # pydubは速くはできるけど遅くできないっぽい？
    def ChangeSpeed(self):
        if self.speed != 1:
            destination_speed = self.speed
            print(self.speed)
            self.sound = self.sound.speedup(playback_speed=self.speed, crossfade=0)
            self.speed = self.len/len(self.sound)
            #print(self.len,len(self.sound))
            log.debug(f'速度倍率: 設定 {destination_speed}  実績 {self.speed}')


# トリミング＆フェード処理
def EditSound(songs):
    log.info('音声編集中...')
    for song in songs:
        song.sound = song.org_sound
        song.Trimming()
        song.fade()
        song.AddSilence()
        #song.ChangeSpeed()
    log.info('音声編集完了')

# クロスフェード
def Xfade(preSong,postSong):
    xfadeBeat = postSong.xfade
    xfadeTime1 = beat2msec(xfadeBeat, preSong.bpm)
    xfadeTime2 = beat2msec(xfadeBeat, postSong.bpm)
    if xfadeTime1 < xfadeTime2:
        silence = AudioSegment.silent(round45(xfadeTime2-xfadeTime1))
        preSong.sound = preSong.sound.append(silence, crossfade=0)
    elif xfadeTime1 > xfadeTime2:
        end = beat2msec(preSong.end, preSong.bpm)
        newEnd = round45(end-(xfadeTime1-xfadeTime2))
        preSong.sound = preSong.sound[:newEnd]
    preSong.len -= xfadeTime1
    preSong.postXfade = msec2beat(xfadeTime2, preSong.bpm)
    return xfadeTime2

# 音声結合
def ConcatenateSongs(songs):
    log.info('音声結合中...')
    sound = songs[0].sound
    for i in range(1,len(songs)):
        xfadeTime = Xfade(songs[i-1],songs[i])
        sound = sound.append(songs[i].sound, crossfade=xfadeTime)
    log.info('音声結合完了')
    return sound

