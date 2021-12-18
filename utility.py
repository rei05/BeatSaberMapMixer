# -*- coding: utf-8 -*-
import os,datetime,json
from decimal import Decimal, ROUND_HALF_UP
import pickle
from PySide6.QtWidgets import QFileDialog,QMessageBox

CWDIR = os.getcwd()
USERDIR = os.path.expanduser('~')
INT32MAX = 2**31-1

DEBUG_MODE = False

EGNPATH = os.path.join(CWDIR, 'Engine')
TMPTEX = os.path.join(CWDIR,'tmp/tmp')
LOGDIR = os.path.join(CWDIR,'Logs')
LOGPATH = None

INFOFILE = 'info.dat'
MAPFILE = 'EasyStandard.dat'
COVERFILE = 'cover.png'

RESOURCE = os.path.join(CWDIR,'resource')
INFORESOURCE = os.path.join(RESOURCE,INFOFILE)
MAPRESOURCE = os.path.join(RESOURCE,MAPFILE)
COVERRESOURCE = os.path.join(RESOURCE,'cover')

COMANDS = ['start','end','xfade','fadein','fadeout','silence']

#pydubのimport前にbinにパスを通す
os.environ['PATH'] = '{};{}'.format(EGNPATH, os.environ['PATH'])

DefaultNJS = 12



class logger():
    def __init__(self, module):
        self.module = module

    def info(self,text):
        _text = f'<{self.module}> [INFO]: {text}'
        print(_text)
        with open(LOGPATH, 'a') as f:
            f.write(_text+'\n')

    def error(self,text):
        _text = f'<{self.module}> [ERROR]: {text}'
        print(_text)
        with open(LOGPATH, 'a') as f:
            f.write(_text+'\n')

    def debug(self,text):
        _text = f'<{self.module}> [DEBUG]: {text}'
        if DEBUG_MODE:
            print(_text)
        with open(LOGPATH, 'a') as f:
            f.write(_text+'\n')


def CreateLogFile():
    now = datetime.datetime.now()
    filename = 'log_' + now.strftime('%Y%m%d_%H%M%S') + '.txt'

    if not os.path.exists(LOGDIR):
        os.mkdir(LOGDIR)
    global LOGPATH
    LOGPATH = os.path.join(LOGDIR,filename)

def SelectDir(self, title, logname, i_split=0):
    # ディレクトリ選択logを確認
    open_dir = USERDIR
    data = {}
    if os.path.exists(TMPTEX):
        try:
            with open(TMPTEX, 'r') as f:
                data = json.load(f)
            open_dir = data[logname]
        except:
            pass
    # 選択ダイアログ
    selected_dir = QFileDialog.getExistingDirectory(self, title, open_dir)
    if len(selected_dir) > 0:        
        # ディレクトリ選択logを書き込み
        parent_dir = selected_dir.rsplit('/',i_split)[0]
        data[logname] = parent_dir
        with open(TMPTEX, 'w') as f:
            json.dump(data,f)
        return selected_dir
    else:
        return False

def CheckOverwrite(path):
    if os.path.exists(path):
        msgBox = QMessageBox()
        msgBox.setWindowTitle('保存先の上書き確認')
        msgBox.setText('選択した場所には指定された保存名のフォルダが既に存在しています。')
        msgBox.setInformativeText('フォルダごと上書きしますか？')
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msgBox.setDefaultButton(QMessageBox.No)
        ret = msgBox.exec()
        if ret == QMessageBox.Yes:
            return True
        else:
            return False
    else:
        os.mkdir(path)
        return True

def CheckBMOverwrite():
    msgBox = QMessageBox()
    msgBox.setWindowTitle('確認')
    msgBox.setText('「出力時、元の譜面ファイルにブックマークコマンド設定を反映する」\n'+
                   'に本当にチェックを付けますか？')
    msgBox.setInformativeText('譜面ファイルへの上書きを行うため、予期せぬ誤動作によりファイルが破損する可能性があります。\n'+
                            'また、既存のブックマークは全てリセットされます。')
    msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msgBox.setDefaultButton(QMessageBox.No)
    ret = msgBox.exec()
    if ret == QMessageBox.Yes:
        return True
    else:
        return False

def msec2timestr(msec):
    td = datetime.timedelta(milliseconds=msec)
    sec = td.seconds%60
    min = td.seconds//60
    return '{:02}:{:02}'.format(min, sec)

def beat2msec(beat, bpm):
    return 60/bpm*beat*1000

def msec2beat(msec, bpm):
    return (msec/1000)/(60/bpm)

def round45(x):
    return int(Decimal(str(x)).quantize(Decimal('0'), rounding=ROUND_HALF_UP))

def HalfJumpDuration(bpm, njs):
    jd = 60/bpm*4*njs*2
    if jd >= 72:
        return 1
    elif jd >=36:
        return 2
    else:
        return 4

def JumpDistance(bpm, njs, offset):
    hjd = HalfJumpDuration(bpm, njs)
    return 60/bpm*max(1,hjd+offset)*njs*2

def HalfLifeSpan(bpm, njs, offset):
    return JumpDistance(bpm, njs, offset)/njs/2

def ConvertOffset(offset_from, njs, bpm_from, bpm_to):
    jd = JumpDistance(bpm_from, njs, offset_from)
    #print(f'JumpDistance: {jd}   {bpm_from} {njs} {offset_from}')
    offset_to = bpm_to*jd/120/njs-HalfJumpDuration(bpm_to, njs)
    return offset_to

def ConvertOffset2(offset_from, njs_from, njs_to, bpm_from, bpm_to):
    hls = HalfLifeSpan(bpm_from, njs_from, offset_from)
    print(f'HalfLifeSpan: {hls}   {bpm_from} {njs_from} {offset_from}')
    offset_to = bpm_to*hls/60-HalfJumpDuration(bpm_to, njs_to)
    return offset_to



def Image2bin(path):
    im = Image.open(path)
    pickle.dump(im, open('resource/cover', 'wb'))

if __name__ == '__main__':
    # exe化前に実行
    
    from PIL import Image
    
    Image2bin(COVERFILE)