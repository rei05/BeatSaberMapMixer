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
        self.silence    = None # [beat]

    def Trimming(self):
        start = round45(beat2msec(self.start, self.bpm))
        end = round45(beat2msec(self.end, self.bpm))
        self.sound = self.sound[start:end]
        log.debug(f'音声トリミング: {msec2timestr(start)}-{msec2timestr(end)}')

    def fade(self):
        if (t_fadein := beat2msec(self.fadein - self.start, self.bpm)) > 0:
            self.sound = self.sound.fade_in(round45(t_fadein))
            log.debug(f'フェードイン: {round45(t_fadein)/1000}sec')
        if (t_fadeout := beat2msec(self.end - self.fadeout, self.bpm)) > 0:
            self.sound = self.sound.fade_out(round45(t_fadeout))
            log.debug(f'フェードアウト: {round45(t_fadeout)/1000}sec')

    def AddSilence(self):
        if (t_silence := beat2msec(self.silence, self.bpm)) < 0:
            silence = AudioSegment.silent(round45(-t_silence))
            self.sound = silence.append(self.sound, crossfade=0)
            log.debug(f'*start前の無音区間: {round45(t_silence)/1000}sec')
        if (t_silence := beat2msec(self.silence, self.bpm)) > 0:
            silence = AudioSegment.silent(round45(t_silence))
            self.sound = self.sound.append(silence, crossfade=0)
            log.debug(f'*end後の無音区間: {round45(t_silence)/1000}sec')


# トリミング＆フェード処理
def EditSound(songlist):
    log.info('音声編集中...')
    for song in songlist:
        song.sound = song.org_sound
        song.Trimming()
        song.fade()
        song.AddSilence()
    log.info('音声編集完了')

# 音声結合
def ConcatenateSongs(songlist):
    log.info('音声結合中...')
    sounds = [song.sound for song in songlist]
    sound = sounds[0]
    for i in range(1,len(songlist)):
        #sound = sound.append(sounds[i], songlist[i].xfade)
        sound = sound.append(sounds[i], crossfade=0)
    log.info('音声結合完了')
    return sound

