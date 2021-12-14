# -*- coding: utf-8 -*-
import os,copy,json
from utility import *
log = logger(__name__)

class Map():
    def __init__(self, map_dir):
        log.info('マップ読み込み中...')
        self.map_dir = map_dir
        self.len = 0 # [msec]
        self.len_beat = 0 # [beat]
        self.level = None
        self.njs = None
        self.org_offset = None
        self.offset = None
        self.timeoffset = 0
        self.n_notes = 0 # for debug
        self.noodle_data = None
        self.start      = None # [beat]
        self.end        = None # [beat]
        self.fadein     = None # [beat]
        self.fadeout    = None # [beat]
        self.xfade      = None # [sec]
        self.presilence = None # [sec]
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
                if map_data := self.ReadDat(filename):
                    self.levels[filename] = {'njs':njs, 'offset':offset, 'dat':map_data}

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
            self.levels[levelname]['start'] = 0
            self.levels[levelname]['end'] = self.len_beat
            self.levels[levelname]['xfade'] = 0
            self.levels[levelname]['fadein'] = 0
            self.levels[levelname]['fadeout'] = self.len_beat
            self.levels[levelname]['presilence'] = 0

        commands = ['start','end','xfade','fadein','fadeout','presilence']
        for levelname in self.levels.keys():

            log.info(f'{levelname}')
            level = self.levels[levelname]
            map_data = level['dat']

            if '_bookmarks' not in map_data['_customData'].keys():
                continue
            if len(map_data['_customData']['_bookmarks'])==0:
                continue

            for com in commands:
                exec(com + '= []')

            for bookmark in map_data['_customData']['_bookmarks']:
                time = bookmark['_time']
                name = bookmark['_name']
                if len(name)==0:
                    continue
                if name[0] == '*':
                    com_detected = False
                    for com in commands:
                        if name[1:] == com:
                            log.info(f'{com}コマンド検出 @{time}')
                            eval(com).append(time)
                            com_detected = True
                    if not com_detected:
                        log.error(f'未定義のコマンド {name} @{time}')

            # 同じコマンドが複数ある場合は最後(timeが最大)のものを適用
            for com in commands:
                if len(eval(com)) > 0:
                    level[com] = max(eval(com))

        # UI表示の初期値をセット
        for com in commands:
            exec('self.' + com + ' = self.levels[self.level]["' + com + '"]')
            
        log.info('ブックマークコマンド検出完了')
                
                

    # Noodle変換
    def ConvertMap(self):
        log.info(f'noodle変換： {self.songname}')
        log.debug(f'map.len: {msec2timestr(self.len)}')
        log.debug(f'map.bpm: {self.bpm}')
        map_data = copy.deepcopy(self.levels[self.level]['dat'])

        # BPMChanges
        log.debug(f'self.start: {self.start}')
        BPMChangetime = self.ConvertTiming(self.start + msec2beat(self.xfade/2, self.bpm))
        BPMChanges = [{"_BPM":self.bpm,"_time":BPMChangetime,"_beatsPerBar":4,"_metronomeOffset":4}]
        if '_BPMChanges' in map_data['_customData'].keys():
            for BPMChange in map_data['_customData']['_BPMChanges']:
                if BPMChange['_time'] == 0:
                    BPMChanges[0] = BPMChange
                if not self.IsDelete(BPMChange['_time']):
                    BPMChange['_time'] = self.ConvertTiming(BPMChange['_time'])
                    BPMChanges.append(BPMChange)
        map_data['_customData']['_BPMChanges'] = BPMChanges

        # bookmarks
        bookmarktime = self.ConvertTiming(self.start + msec2beat(self.xfade/2, self.bpm))
        map_data['_customData']['_bookmarks'] = [{"_time":bookmarktime,"_name":self.songname}]
        
        # pointDefinitions
        if '_pointDefinitions' not in map_data['_customData'].keys():
            map_data['_customData']['_pointDefinitions'] = []

        # customEvents
        customEvents = []
        if '_customEvents' in map_data['_customData'].keys():
            for customEvent in map_data['_customData']['_customEvents']:
                if not self.IsDelete(customEvent['_time']):
                    customEvent['_time'] = self.ConvertTiming(customEvent['_time'])
                    if '_duration' in customEvent['_data'].keys():
                        customEvent['_data']['_duration'] = self.ConvertTiming(customEvent['_data']['_duration'],0)
                    customEvents.append(customEvent)
        map_data['_customData']['_customEvents'] = customEvents

        # events
        events = []
        for event in map_data['_events']:
            if not self.IsDelete(event['_time']):
                event['_time'] = self.ConvertTiming(event['_time'])
                events.append(event)
        map_data['_events'] = events

        # notes
        notes = []
        for note in map_data['_notes']:
            if not self.IsDelete(note['_time']):
                note['_time'] = self.ConvertTiming(note['_time'])
                note = self.SetObjectsMove(note)
                notes.append(note)
        map_data['_notes'] = notes

        # obstacles
        obstacles = []
        for obst in map_data['_obstacles']:
            if not self.IsDelete(obst['_time']):
                obst['_time'] = self.ConvertTiming(obst['_time'])
                obst['_duration'] = self.ConvertTiming(obst['_duration'],0)
                obst = self.SetObjectsMove(obst)
                obstacles.append(obst)
        map_data['_obstacles'] = obstacles

        self.noodle_data = map_data

    # トリミングによるオブジェクトの削除判定
    def IsDelete(self,t):
        return (t < self.start + msec2beat(self.xfade*(3/4), self.bpm)) | (t >= self.end)

    # タイミング変換
    def ConvertTiming(self,b,timeoffset=None):
        dt = self.timeoffset if timeoffset is None else timeoffset
        time = b*(DefaultBPM/self.bpm) + msec2beat(dt, DefaultBPM)
        time = round(time,6)
        assert time >= 0
        return time

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


class NewMap():
    def __init__(self, dir, maplist):
        self.dir = dir
        self.maplist = maplist
        self.map_data = None
        global DefaultBPM
        # NJSがBPMの15%以上だとオフセット変更できない
        # -> 結合するマップの中で最大のNJSが全体BPMの15%以下の値になるようにする
        DefaultBPM = max(max([map.njs for map in maplist])/0.15, max([map.bpm for map in maplist]))
        log.debug(f'DefaultBPM: {DefaultBPM}')
        with open(INFORESOURCE,'r') as f:
            self.info = json.load(f)
        self.info['_beatsPerMinute'] = DefaultBPM
        self.info['_difficultyBeatmapSets'][0]['_difficultyBeatmaps'][0]['_noteJumpMovementSpeed'] = DefaultNJS
        self.ConcatenateMaps()
        self.CreateMap()

    # マップ結合
    def ConcatenateMaps(self):
        log.info('マップデータ処理中...')
        with open(MAPRESOURCE,'r') as f:
            newmap_data = json.load(f)
        
        timeoffset = 0 # 前の譜面までの合計時間[msec]
        for i in range(len(self.maplist)):
            pre_map = self.maplist[i-1]
            map = self.maplist[i]
            timeoffset += pre_map.len if i!=0 else 0
            timeoffset -= map.xfade if i!=0 else 0
            log.debug(f'timeoffset: {msec2timestr(timeoffset)}')
            log.debug(f'start: {msec2timestr(beat2msec(map.start, map.bpm))}')
            map.timeoffset = timeoffset - beat2msec(map.start, map.bpm)
            
            map.ConvertMap()
            
            map_data = map.noodle_data
            map.n_notes = len(map_data["_notes"])

            newmap_data['_customData']['_BPMChanges'].extend(map_data['_customData']['_BPMChanges'])
            newmap_data['_customData']['_bookmarks'].extend(map_data['_customData']['_bookmarks'])
            newmap_data['_customData']['_pointDefinitions'].extend(map_data['_customData']['_pointDefinitions'])
            newmap_data['_customData']['_customEvents'].extend(map_data['_customData']['_customEvents'])
            newmap_data['_events'].extend(map_data['_events'])
            newmap_data['_notes'].extend(map_data['_notes'])
            newmap_data['_obstacles'].extend(map_data['_obstacles'])
        self.map_data = newmap_data
        log.info('マップデータ処理完了')

    # マップデータ出力
    def CreateMap(self):
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