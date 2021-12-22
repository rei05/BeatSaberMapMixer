# -*- coding: utf-8 -*-
import os,copy,json
from utility import *
log = logger(__name__)

class Map():
    def __init__(self, map_dir):
        log.info('マップ読み込み中...')
        self.map_dir = map_dir
        self.len = 0 # [msec]
        self.level = None
        self.njs = None
        self.org_offset = None
        self.offset = None
        self.timeOffset = None # [msec]
        self.mapData    = None
        self.speed      = 1.0 # scale
        self.start      = None # [beat]
        self.end        = None # [beat]
        self.fadein     = None # [beat]
        self.fadeout    = None # [beat]
        self.xfade      = None # [beat]
        self.silence    = None # [beat]
        self.postXfade  = 0    # [beat]
        self.info_data = self.ReadDat('info.dat')
        if self.info_data:
            if self.ReadInfo():
                self.org_offset = self.offset
                self.valid = True
            else:
                self.valid = False
        else:
            self.valid = False
    
    # datファイル読み込み
    def ReadDat(self,file):
        log.info(f'{file}読み込み')
        file_path = os.path.join(self.map_dir, file)
        if os.path.exists(file_path):
            with open(file_path,'r',encoding='utf_8') as f:
                try:
                    data = json.load(f)
                    return data
                except:
                    log.error(f'{file}の中身が不正です！')
                    return False
        else:
            log.error(f'{file}が見つかりません！')
            return False

    # info.datパース
    def ReadInfo(self):
        log.info('info.dat解析中...')
        self.songname = self.info_data['_songName']
        self.songsubname = self.info_data['_songSubName']
        self.levelauthor = self.info_data['_levelAuthorName']
        self.bpm = self.info_data['_beatsPerMinute']
        self.bpm2 = self.bpm
        self.songauthor = self.info_data['_songAuthorName']
        self.songfile = os.path.join(self.map_dir,self.info_data['_songFilename'])
        self.songfilename = self.info_data['_songFilename']
        self.coverimg = os.path.join(self.map_dir,self.info_data['_coverImageFilename'])
        self.levels = {}

        # レベルごとの情報
        for mapset in self.info_data['_difficultyBeatmapSets']:
            for level in mapset['_difficultyBeatmaps']:
                filename = level['_beatmapFilename']
                njs = level['_noteJumpMovementSpeed']
                offset = level['_noteJumpStartBeatOffset']
                if mapData := self.ReadDat(filename):
                    self.levels[filename] = {'njs':njs, 'offset':offset, 'dat':mapData}

        if len(self.levels) == 0:
            log.error('読み込み可能なレベルがありません！')
            return False
        
        # UI表示の初期値をセット
        init_level = self.info_data['_difficultyBeatmapSets'][0]['_difficultyBeatmaps'][0]
        self.level = init_level['_beatmapFilename']
        self.njs = init_level['_noteJumpMovementSpeed']
        self.offset = init_level['_noteJumpStartBeatOffset']
        log.info('info.dat解析完了')
        return True


    # ブックマークコマンドパース
    def CommandParse(self):
        log.info('ブックマークコマンド検出中...')

        for levelname in self.levels.keys():

            log.info(f'{levelname}')
            level = self.levels[levelname]
            mapData = level['dat']

            level['start']   = 0
            level['end']     = msec2beat(self.len, self.bpm)
            level['fadein']  = 0
            level['fadeout'] = msec2beat(self.len, self.bpm)
            level['xfade']   = 0
            level['silence'] = 0

            if '_bookmarks' not in mapData['_customData'].keys():
                continue
            if len(mapData['_customData']['_bookmarks'])==0:
                continue

            start, end, fadein, fadeout, xfade, silence = [], [], [], [], [], []
            
            for bookmark in mapData['_customData']['_bookmarks']:
                time = bookmark['_time']
                name = bookmark['_name']
                if len(name)==0:
                    continue
                if name[0] == '*':
                    com_detected = False
                    for com in COMANDS:
                        if com in name[1:]:
                            log.info(f'{com}コマンド検出 @{time}')
                            eval(com).append(time)
                            com_detected = True
                    if not com_detected:
                        log.error(f'未定義のコマンド {name} @{time}')

            # ブックマークコマンド無しの場合は初期値をセット
            # 同じコマンドが複数ある場合は最後(timeが最大)のものを適用
            level['start']   = max(start)   if len(start)   > 0 else 0
            level['end']     = max(end)     if len(end)     > 0 else msec2beat(self.len, self.bpm)
            level['fadein']  = max(fadein)  if len(fadein)  > 0 else level['start']
            level['fadeout'] = max(fadeout) if len(fadeout) > 0 else level['end']
            level['xfade']   = max(xfade)   if len(xfade)   > 0 else level['start']
            level['silence'] = max(silence) if len(silence) > 0 else 0

            # silenceコマンドのパース
            for bookmark in mapData['_customData']['_bookmarks']:
                time = bookmark['_time']
                name = bookmark['_name']
                if time==level['silence']:
                    try:
                        level['silence'] = float(name[8:])
                    except:
                        log.error(f'silenceコマンドのパラメータが不正です！　@{time}')
                        level['silence'] = 0

        # UI表示の初期値をセット
        level = self.levels[self.level]
        self.start = level['start']
        self.end = level['end']
        self.xfade = xfade if (xfade := level['xfade']-level['start']) > 0 else 0 
        self.fadein = fadein if (fadein := level['fadein']-level['start']) > 0 else 0 
        self.fadeout = fadeout if (fadeout := level['end']-level['fadeout']) > 0 else 0 
        self.silence = level['silence']

        log.info('ブックマークコマンド検出完了')
                

    # BPMChanges
    def ConvertBPMChanges(self):
        BPMChangetime = self.ConvertTiming(self.start - max(0, -self.silence) + self.xfade/2)
        BPMChanges = [{"_BPM":self.bpm,"_time":BPMChangetime,"_beatsPerBar":4,"_metronomeOffset":4}]
        if '_BPMChanges' in self.mapData['_customData'].keys():
            for BPMChange in self.mapData['_customData']['_BPMChanges']:
                if BPMChange['_time'] == 0:
                    BPMChanges[0] = BPMChange
                if not self.IsDelete(BPMChange['_time']):
                    BPMChange['_time'] = self.ConvertTiming(BPMChange['_time'])
                    BPMChanges.append(BPMChange)
        self.mapData['_customData']['_BPMChanges'] = BPMChanges

    # Bookmarks
    def ConvertBookmarks(self):
        bookmarktime = self.ConvertTiming(self.start - max(0, -self.silence) + self.xfade/2)
        if bookmarktime == 0:
            bookmarktime += 1e-5
        self.mapData['_customData']['_bookmarks'] = [{"_time":bookmarktime,"_name":self.songname}]

    # pointDefinitions
    def ConvertPointDefinitions(self):
        if '_pointDefinitions' not in self.mapData['_customData'].keys():
            self.mapData['_customData']['_pointDefinitions'] = []

    # customEvents
    def ConvertCustomEvents(self):
        customEvents = []
        if '_customEvents' in self.mapData['_customData'].keys():
            for customEvent in self.mapData['_customData']['_customEvents']:
                if not self.IsDelete(customEvent['_time']):
                    customEvent['_time'] = self.ConvertTiming(customEvent['_time'])
                    if '_duration' in customEvent['_data'].keys():
                        customEvent['_data']['_duration'] = self.ConvertTiming(customEvent['_data']['_duration'],1)
                    customEvents.append(customEvent)
        self.mapData['_customData']['_customEvents'] = customEvents

    # events
    def ConvertEvents(self):
        events = []
        for event in self.mapData['_events']:
            if not self.IsDelete(event['_time']):
                event['_time'] = self.ConvertTiming(event['_time'])
                if '_customData' in event.keys():
                    if '_lightGradient' in event['_customData'].keys():
                        event['_customData']['_lightGradient']['_duration'] = self.ConvertTiming(event['_customData']['_lightGradient']['_duration'],1)
                events.append(event)
        self.mapData['_events'] = events

    # notes
    def ConvertNotes(self):
        notes = []
        for note in self.mapData['_notes']:
            if not self.IsDelete(note['_time']):
                note['_time'] = self.ConvertTiming(note['_time'])
                note = self.SetObjectsMove(note)
                notes.append(note)
        self.mapData['_notes'] = notes

    # obstacles
    def ConvertObstacles(self):
        obstacles = []
        for obst in self.mapData['_obstacles']:
            if not self.IsDelete(obst['_time']):
                obst['_time'] = self.ConvertTiming(obst['_time'])
                obst['_duration'] = self.ConvertTiming(obst['_duration'],1)
                obst = self.SetObjectsMove(obst)
                obstacles.append(obst)
        self.mapData['_obstacles'] = obstacles 

    # Noodle変換
    def ConvertMap(self):
        self.mapData = copy.deepcopy(self.levels[self.level]['dat'])
        self.ConvertBPMChanges()
        self.ConvertBookmarks()
        self.ConvertPointDefinitions()
        self.ConvertCustomEvents()
        self.ConvertEvents()
        self.ConvertNotes()
        self.ConvertObstacles()

    # トリミングによるオブジェクトの削除判定
    def IsDelete(self,t):
        return (t < self.start + self.xfade/2) | (t >= self.end - self.postXfade/2)

    # タイミング変換
    def ConvertTiming(self,beat, duration_mode=0):
        preMapOffset = 0 if duration_mode else msec2beat(self.timeOffset, DefaultBPM)
        preSilence = max(0, -self.silence)
        newBeat = (beat*(DefaultBPM/self.bpm) + preSilence)/self.speed + preMapOffset
        newBeat = round(newBeat,4)
        try:
            assert newBeat >= 0
        except(AssertionError):
            log.debug(f'[AssertionError] ConvertTiming newBeat={newBeat}')
        return newBeat

    # NJS,offset変換
    def SetObjectsMove(self,object):
        org_njs = self.levels[self.level]['njs']
        '''
        log.debug(f'self.BPM: {self.bpm}')
        log.debug(f'DefaultBPM: {DefaultBPM}')
        log.debug(f'org_njs: {org_njs}')
        log.debug(f'self.njs: {self.njs}')
        log.debug(f'self.offset: {self.offset}')
        '''
        general_new_offset = ConvertOffset(self.offset, org_njs, self.bpm, DefaultBPM)
        #log.debug(f'general_new_offset: {general_new_offset}')
        if '_customData' in object.keys():
            if '_noteJumpMovementSpeed' in object['_customData'].keys():
                noodle_njs = object['_customData']['_noteJumpMovementSpeed']
            else:
                noodle_njs = org_njs
                object['_customData']['_noteJumpMovementSpeed'] = self.njs
            if '_noteJumpStartBeatOffset' in object['_customData'].keys():
                org_offset = object['_customData']['_noteJumpStartBeatOffset']
                #new_offset = ConvertOffset(org_offset , noodle_njs, self.bpm, DefaultBPM)
                #object['_customData']['_noteJumpStartBeatOffset'] = new_offset
            else:
                object['_customData']['_noteJumpStartBeatOffset'] = general_new_offset
        else:
            object['_customData'] = {'_noteJumpMovementSpeed':self.njs,
                                   '_noteJumpStartBeatOffset':general_new_offset}
        return object

    def CommandOverwrite(self):
        bookmarks = []
        bookmarks.append({'_time':self.start, '_name':'*start'})
        bookmarks.append({'_time':self.end, '_name':'*end'})
        if self.fadein != 0:
            bookmarks.append({'_time':self.start+self.fadein, '_name':'*fadein'})
        if self.fadeout != 0:
            bookmarks.append({'_time':self.end-self.fadeout, '_name':'*fadeout'})
        if self.xfade != 0:
            bookmarks.append({'_time':self.start+self.xfade, '_name':'*xfade'})
        if self.silence !=0:
            bookmarks.append({'_time':self.start+0.25, '_name':'*silence'+str(self.silence)})
        mapData = self.ReadDat(self.level)
        mapData['_customData']['_bookmarks'] = bookmarks
        with open(os.path.join(self.map_dir,self.level),'w') as f:
            json.dump(mapData,f,indent=4)

class NewMap():
    def __init__(self, dir, maps):
        self.dir = dir
        self.maps = maps
        self.map_data = None
        self.sound = None
        global DefaultBPM
        # NJSがBPMの15%以上だとオフセット変更できない
        # -> 結合するマップの中で最大のNJSが全体BPMの15%以下の値になるようにする
        DefaultBPM = max(max([map.njs for map in maps])/0.15, max([map.bpm for map in maps]))
        log.debug(f'DefaultBPM: {DefaultBPM}')
        with open(INFORESOURCE,'r') as f:
            self.info = json.load(f)
        self.info['_beatsPerMinute'] = DefaultBPM
        self.info['_difficultyBeatmapSets'][0]['_difficultyBeatmaps'][0]['_noteJumpMovementSpeed'] = DefaultNJS

    # 前の譜面までの合計時間[msec]
    def CalcTimeOffset(self):
        timeOffset = 0
        self.maps[0].timeOffset = timeOffset - beat2msec(self.maps[0].start, self.maps[0].bpm)
        log.debug(f'{self.maps[0].songname}')
        log.debug(f'timeOffset: {msec2timestr(timeOffset)}')
        for i in range(1,len(self.maps)):
            log.debug(f'{self.maps[i].songname}')
            timeOffset += self.maps[i-1].len
            self.maps[i].timeOffset = timeOffset - beat2msec(self.maps[i].start, self.maps[i].bpm)
            log.debug(f'timeOffset: {msec2timestr(timeOffset)}')

    # マップ結合
    def ConcatenateMaps(self):
        log.info('マップデータ処理中...')
        with open(MAPRESOURCE,'r') as f:
            newmap_data = json.load(f)
        
        for i in range(len(self.maps)):
            
            self.maps[i].ConvertMap()
            mapData = self.maps[i].mapData

            newmap_data['_customData']['_BPMChanges'].extend(mapData['_customData']['_BPMChanges'])
            newmap_data['_customData']['_bookmarks'].extend(mapData['_customData']['_bookmarks'])
            newmap_data['_customData']['_pointDefinitions'].extend(mapData['_customData']['_pointDefinitions'])
            newmap_data['_customData']['_customEvents'].extend(mapData['_customData']['_customEvents'])
            if '_environment' in mapData['_customData'].keys():
                newmap_data['_customData']['_environment'].extend(mapData['_customData']['_environment'])
            newmap_data['_events'].extend(mapData['_events'])
            newmap_data['_notes'].extend(mapData['_notes'])
            newmap_data['_obstacles'].extend(mapData['_obstacles'])
        self.map_data = newmap_data
        log.info('マップデータ処理完了')

    # マップデータ出力
    def OutputMap(self):
        log.info('datファイル出力中...')
        if not os.path.exists(self.dir):
            os.mkdir(self.dir)

        im = pickle.load(open(COVERRESOURCE,'rb'))
        im.save(os.path.join(self.dir,COVERFILE))

        with open(os.path.join(self.dir,INFOFILE),'w') as f: 
            json.dump(self.info, f)

        with open(os.path.join(self.dir,MAPFILE),'w') as f:
            json.dump(self.map_data, f)
        log.info('datファイル出力完了！')

        log.info('oggファイル出力中...')
        self.sound.export(os.path.join(self.dir,"song.ogg"), format="ogg")
        log.info('oggファイル出力完了！')