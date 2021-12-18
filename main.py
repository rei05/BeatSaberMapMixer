# -*- coding: utf-8 -*-

##-MEMO-####################################################
# exe化コマンド
#   pyinstaller main.py --onefile --clean
#   ※[--noconsole]オプション付けるとffmpegのコンソール起動と
#     競合して動作しなくなる。
# ui → py変換コマンド
#   uic.exe main.ui -o ui.py -g python
############################################################

import os,sys,textwrap,time
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWidgets import QMessageBox
from ui import Ui_MainWindow
from MapManager import Map, NewMap
from SoundProcessor import Song, ConcatenateSongs,EditSound
from utility import *
log = logger(__name__)


class UI(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(UI, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle('BeatSaberMapMixer')
        self.iSlot = 0 #スロット番号(表示上は1始まり)
        self.nSlot = 1 #スロット数
        self.maps = [None]*32
        self.songs = [None]*32

        self.ui.BMOverwriteCheckAction.changed.connect(self.click_BMOverwriteCheck)
        
        ToolTipDuration = 30000
        self.ui.startLabel.setToolTip('<b>*start</b><br>曲の開始位置をbeatで指定します。')
        self.ui.endLabel.setToolTip('<b>*end</b><br>曲の終了位置をbeatで指定します。')
        self.ui.xfadeLabel.setToolTip('<b>*xfade</b><br>前の曲とのクロスフェードにかける時間長をbeatで指定します。')
        self.ui.fadeinLabel.setToolTip('<b>*fadein</b><br>フェードインにかける時間をbeatで指定します。')
        self.ui.fadeoutLabel.setToolTip('<b>*fadeout</b><br>フェードアウトにかける時間をbeatで指定します。')
        self.ui.silenceLabel.setToolTip('<b>*silence</b><br>*endの直後に挿入する無音区間の長さをbeatで指定します。負の数を指定した場合は*startの直前に挿入します。')
        self.ui.startLabel.setToolTipDuration(ToolTipDuration)
        self.ui.endLabel.setToolTipDuration(ToolTipDuration)
        self.ui.xfadeLabel.setToolTipDuration(ToolTipDuration)
        self.ui.fadeinLabel.setToolTipDuration(ToolTipDuration)
        self.ui.fadeoutLabel.setToolTipDuration(ToolTipDuration)
        self.ui.silenceLabel.setToolTipDuration(ToolTipDuration)

        self.ui.addButton.clicked.connect(self.click_addButton)
        self.ui.deleteButton.clicked.connect(self.click_deleteButton)
        
        self.ui.nextButton.clicked.connect(self.click_nextButton)
        self.ui.backButton.clicked.connect(self.click_backButton)
               
        self.ui.setDefaultNJSButton.clicked.connect(self.setDefaultNJS)
        self.ui.setDefaultOffsetButton.clicked.connect(self.setDefaultOffset)
        #self.ui.setDefaultBPMButton.clicked.connect(self.setDefaultBPM)
        
        self.ui.lineEdit.setText("Generated_Map")
        self.ui.outputButton.clicked.connect(self.click_outputButton)

        self.connect_parameter()
        self.clear_map_info()

    
    # マップ選択ボタン
    def click_addButton(self):
        if not (selected_dir := SelectDir(self, 'マップ選択', 'input_dir', i_split=1)):
            log.info('マップ読み込みはキャンセルされました。')
            return 0

        map = Map(selected_dir)
        if not map.valid:
            log.error('マップが読み込めませんでした!')
            return 0

        # マップ読み込み成功ならばマップ情報を上書き
        self.maps[self.iSlot] = map
        song = Song(map.songfile, map.bpm)
        self.songs[self.iSlot] = song
        map.len = song.len
        map.CommandParse()

        # 表示系更新
        self.disconnect_parameter()
        self.clear_map_info()
        self.set_map_info()

    def set_map_info(self):
        log.info('マップ情報をセット')
        map = self.maps[self.iSlot]

        self.ui.SongNameLabel.setText(textwrap.shorten(map.songname, 40))
        self.ui.SongSubNameLabel.setText(textwrap.shorten(map.songsubname, 40))
        self.ui.SongArtistLabel.setText(textwrap.shorten(map.songauthor, 40))
        self.ui.MapperLabel.setText(textwrap.shorten(map.levelauthor, 40))
        self.ui.BPMLabel.setText('{:.2f}'.format(map.bpm))
        self.ui.AudioFileLabel.setText(map.songfilename)
        self.ui.JDLabel.setText('{:.2f}'.format(JumpDistance(map.bpm, map.njs, map.offset)))

        self.ui.NJSSpinBox.setValue(map.njs)
        self.ui.OffsetSpinBox.setValue(map.offset)
        #self.ui.BPMSpinBox.setValue(map.bpm2)
        self.ui.NJSSpinBox.setEnabled(True)
        self.ui.OffsetSpinBox.setEnabled(True)
        #self.ui.BPMSpinBox.setEnabled(True)

        self.ui.setDefaultNJSButton.setEnabled(True)
        self.ui.setDefaultOffsetButton.setEnabled(True)
        #self.ui.setDefaultBPMButton.setEnabled(True)

        self.ui.comboBox.addItems(list(map.levels.keys()))
        self.ui.comboBox.setCurrentText(map.level)
        self.ui.comboBox.setEnabled(True)

        self.ui.startSpinBox.setValue(map.start)
        self.ui.endSpinBox.setValue(map.end)
        self.ui.fadeinSpinBox.setValue(map.fadein)
        self.ui.fadeoutSpinBox.setValue(map.fadeout)
        self.ui.silenceSpinBox.setValue(map.silence)
        self.ui.startSpinBox.setEnabled(True)
        self.ui.endSpinBox.setEnabled(True)
        if self.iSlot != 0:
            self.ui.xfadeSpinBox.setEnabled(True)
            self.ui.xfadeSpinBox.setValue(map.xfade)
        else:
            self.ui.xfadeSpinBox.setEnabled(False)
            self.ui.xfadeSpinBox.setValue(0)
            map.xfade = 0
        self.ui.fadeinSpinBox.setEnabled(True)
        self.ui.fadeoutSpinBox.setEnabled(True)
        self.ui.silenceSpinBox.setEnabled(True)

        self.connect_parameter()

        cover = QtGui.QPixmap(map.coverimg)
        self.ui.coverLabel.setPixmap(cover)
        self.ui.coverLabel.setScaledContents(True)

        self.ui.deleteButton.setEnabled(True)
        self.update_slot()

        if self.maps[0] is not None:
            self.ui.lineEdit.setEnabled(True)
            self.ui.outputButton.setEnabled(True)

    # comboBox内容(level)の変更を検知したとき呼ばれる
    def update_level(self):
        log.debug('update_level')
        self.disconnect_parameter()
        map = self.maps[self.iSlot]
        map.level = self.ui.comboBox.currentText()
        selected_level = map.levels[map.level]

        map.njs = selected_level['njs']
        map.offset = selected_level['offset']
        map.start = selected_level['start']
        map.end = selected_level['end']
        map.xfade = xfade if (xfade := selected_level['xfade']-selected_level['start']) > 0 else 0 
        map.fadein = fadein if (fadein := selected_level['fadein']-selected_level['start']) > 0 else 0 
        map.fadeout = fadeout if (fadeout := selected_level['end']-selected_level['fadeout']) > 0 else 0 
        map.silence = selected_level['silence']

        self.ui.NJSSpinBox.setValue(map.njs)
        self.ui.OffsetSpinBox.setValue(map.offset)
        #self.ui.BPMSpinBox.setValue(map.bpm)
        self.ui.JDLabel.setText('{:.2f}'.format(JumpDistance(map.bpm, map.njs, map.offset)))
        self.ui.startSpinBox.setValue(map.start)
        self.ui.endSpinBox.setValue(map.end)
        self.ui.xfadeSpinBox.setValue(map.xfade)
        self.ui.fadeinSpinBox.setValue(map.fadein)
        self.ui.fadeoutSpinBox.setValue(map.fadeout)
        self.ui.silenceSpinBox.setValue(map.silence)
        
        self.connect_parameter()
        log.info(f'レベル選択: {map.level}')

    # SpinBox内容の変更を検知したとき呼ばれる
    def update_parameter(self):
        log.debug('update_parameter')
        map = self.maps[self.iSlot]
        map.njs = self.ui.NJSSpinBox.value()
        map.offset = self.ui.OffsetSpinBox.value()
        #map.bpm2 = self.ui.BPMSpinBox.value()
        self.ui.JDLabel.setText('{:.2f}'.format(JumpDistance(map.bpm, map.njs, map.offset)))
        map.start = self.ui.startSpinBox.value()
        map.end = self.ui.endSpinBox.value()
        map.xfade = self.ui.xfadeSpinBox.value()
        map.fadein = self.ui.fadeinSpinBox.value()
        map.fadeout = self.ui.fadeoutSpinBox.value()
        map.silence = self.ui.silenceSpinBox.value()
        log.debug(f'BPM:{map.bpm2} NJS:{map.njs} OFFSET:{map.offset}')
        log.debug(f'*start:{map.start} *end:{map.end}')
        log.debug(f'*fadein:{map.fadein} *fadeout:{map.fadeout}')
        log.debug(f'*xfade:{map.xfade} *silence:{map.fadeout}')

    def setDefaultNJS(self):
        log.info('NJSを既定値に戻す')
        map = self.maps[self.iSlot]
        level = self.ui.comboBox.currentText()
        map.njs = map.levels[level]['njs']
        self.ui.NJSSpinBox.setValue(map.njs)

    def setDefaultOffset(self):
        log.info('OFFSETを既定値に戻す')
        map = self.maps[self.iSlot]
        level = self.ui.comboBox.currentText()
        map.offset = map.levels[level]['offset']
        self.ui.OffsetSpinBox.setValue(map.offset)

    '''
    def setDefaultBPM(self):
        log.info('BPMを既定値に戻す')
        map = self.maps[self.iSlot]
        self.ui.BPMSpinBox.setValue(map.bpm)
    '''

    # comboBox/SpinBoxの内容変更の検知を有効にする
    def connect_parameter(self):
        log.debug('connect_parameter')
        self.ui.comboBox.currentTextChanged.connect(self.update_level)
        self.ui.NJSSpinBox.textChanged.connect(self.update_parameter)
        self.ui.OffsetSpinBox.textChanged.connect(self.update_parameter)
        #self.ui.BPMSpinBox.textChanged.connect(self.update_parameter)
        self.ui.startSpinBox.textChanged.connect(self.update_parameter)
        self.ui.endSpinBox.textChanged.connect(self.update_parameter)
        self.ui.xfadeSpinBox.textChanged.connect(self.update_parameter)
        self.ui.fadeinSpinBox.textChanged.connect(self.update_parameter)
        self.ui.fadeoutSpinBox.textChanged.connect(self.update_parameter)
        self.ui.silenceSpinBox.textChanged.connect(self.update_parameter)

    # comboBox/SpinBoxの内容変更の検知を無効にする
    def disconnect_parameter(self):
        log.debug('disconnect_parameter')
        self.connect_parameter()
        self.ui.comboBox.currentTextChanged.disconnect()
        self.ui.NJSSpinBox.textChanged.disconnect()
        self.ui.OffsetSpinBox.textChanged.disconnect()
        #self.ui.BPMSpinBox.textChanged.disconnect()
        self.ui.startSpinBox.textChanged.disconnect()
        self.ui.endSpinBox.textChanged.disconnect()
        self.ui.xfadeSpinBox.textChanged.disconnect()
        self.ui.fadeinSpinBox.textChanged.disconnect()
        self.ui.fadeoutSpinBox.textChanged.disconnect()
        self.ui.silenceSpinBox.textChanged.disconnect()

    # スロット表示＆移動ボタンの更新
    def update_slot(self):
        # 1ページ目より前には戻れない
        if self.iSlot == 0 :
            self.ui.backButton.setEnabled(False)
        else:
            self.ui.backButton.setEnabled(True)
        
        # カレントスロットが空(最後尾)orスロット数MAXなら進めない
        if (self.maps[self.iSlot] is None)|(self.iSlot == len(self.maps)-1):
            self.ui.nextButton.setText('╋')
            self.ui.nextButton.setEnabled(False)
        else:
            self.ui.nextButton.setEnabled(True)
            if self.iSlot+1 == self.nSlot:
                self.ui.nextButton.setText('╋')
            else:
                self.ui.nextButton.setText('▶')
        n_map = len([map for map in self.maps if map is not None])
        self.ui.iSlotLabel.setText(f'#{self.iSlot+1} / {n_map}')

    # マップ情報のラベルテキストをクリア
    def clear_map_info(self, init=False):
        log.debug(f'表示情報をクリア')
        self.disconnect_parameter()

        self.ui.SongNameLabel.clear()
        self.ui.SongSubNameLabel.clear()
        self.ui.SongArtistLabel.clear()
        self.ui.MapperLabel.clear()
        self.ui.BPMLabel.clear()
        self.ui.AudioFileLabel.clear()
        self.ui.coverLabel.clear()
        self.ui.JDLabel.clear()

        self.ui.deleteButton.setEnabled(False)     

        self.ui.comboBox.clear()
        self.ui.comboBox.setEnabled(False)

        self.ui.NJSSpinBox.clear()
        self.ui.OffsetSpinBox.clear()
        #self.ui.BPMSpinBox.clear()
        self.ui.NJSSpinBox.setEnabled(False)
        self.ui.OffsetSpinBox.setEnabled(False)
        #self.ui.BPMSpinBox.setEnabled(False)

        self.ui.setDefaultNJSButton.setEnabled(False)
        self.ui.setDefaultOffsetButton.setEnabled(False)
        #self.ui.setDefaultBPMButton.setEnabled(False)
        self.update_slot()

        self.ui.startSpinBox.clear()
        self.ui.endSpinBox.clear()
        self.ui.xfadeSpinBox.clear()
        self.ui.fadeinSpinBox.clear()
        self.ui.fadeoutSpinBox.clear()
        self.ui.silenceSpinBox.clear()
        self.ui.startSpinBox.setEnabled(False)
        self.ui.endSpinBox.setEnabled(False)
        self.ui.xfadeSpinBox.setEnabled(False)
        self.ui.fadeinSpinBox.setEnabled(False)
        self.ui.fadeoutSpinBox.setEnabled(False)
        self.ui.silenceSpinBox.setEnabled(False)

        if self.maps[0] is None:
            self.ui.lineEdit.setEnabled(False)
            self.ui.outputButton.setEnabled(False)

   # スロット削除ボタン
    def click_deleteButton(self):

        # カレントスロットが空でない場合のみ
        if self.maps[self.iSlot] is not None:
            # 削除確認ダイアログ
            msgBox = QMessageBox()
            msgBox.setWindowTitle('スロットの削除確認')
            msgBox.setText('本当に削除しますか？')
            msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msgBox.setDefaultButton(QMessageBox.No)
            ret = msgBox.exec()

            # Yesならばスロット削除
            if ret == QMessageBox.Yes:
                self.maps.pop(self.iSlot)
                self.songs.pop(self.iSlot)
                self.clear_map_info()
                self.nSlot -= 1
                log.info(f'スロット#{self.iSlot+1}を削除')

                # 最後尾スロットを削除した場合、カレントスロットを1つ前に移す
                if self.iSlot > self.nSlot-1:
                    # 最後尾=先頭の場合はスロット変化なし
                    if self.nSlot==0:
                        self.nSlot += 1
                    else:
                        self.iSlot -= 1
                        self.set_map_info()
                
                # 最後尾1つ前のスロットを削除した場合
                elif self.iSlot == self.nSlot-1:
                    # 最後尾が空のとき
                    if self.maps[self.iSlot] is None:
                        self.clear_map_info()
                    # 最後尾が空でないとき
                    else:
                        self.set_map_info()
                
                # その他のスロットを削除した場合
                else:
                    self.set_map_info()
                log.info(f'現在のスロットは#{self.iSlot+1} / {self.nSlot}')


    # 次のスロットへ進むボタン
    def click_nextButton(self):
        
        # カレントスロットが空でない場合
        if self.maps[self.iSlot] is not None:
            self.clear_map_info()

            # カレントスロットが最後尾のとき
            if (self.iSlot == self.nSlot-1):
                self.iSlot += 1
                self.nSlot += 1
                log.info(f'スロット#{self.iSlot}を追加')
            
            # カレントスロットが最後尾でないとき
            else:
                # 次のスロットも空でないとき
                self.clear_map_info()
                self.iSlot += 1
                if self.maps[self.iSlot] is not None:
                    self.set_map_info()
                log.info(f'スロット#{self.iSlot}へ進む')

            self.update_slot()

        # カレントスロットが空(=最後尾が空)の場合は新規作成不可
        else:
            pass

    # 前のスロットへ戻るボタン
    def click_backButton(self):
        # インデックス0より前へは戻らない
        if self.iSlot-1 < 0:
            pass
        else:
            self.clear_map_info()
            self.iSlot -= 1
            self.set_map_info()
            self.update_slot()
            log.info(f'スロット#{self.iSlot}へ戻る ')

    def click_BMOverwriteCheck(self):
        if self.ui.BMOverwriteCheckAction.isChecked():
            if not CheckBMOverwrite():
                self.ui.BMOverwriteCheckAction.setChecked(False)

    # 出力ボタン
    def click_outputButton(self):
        save_name = self.ui.lineEdit.text()
        if save_name == '':
            QMessageBox.information(self.ui, '保存名未指定', '保存名を指定してください!', QMessageBox.Ok)

        if not (selected_dir := SelectDir(self, '保存先選択', 'output_dir', i_split=0)):
            log.info('出力はキャンセルされました')
            return 0

        output_path = os.path.join(selected_dir, save_name)

        self.ui.outputButton.setEnabled(False)
        self.ui.outputButton.setText('出力中...')

        if CheckOverwrite(output_path):
            self.output_map(output_path)

        self.ui.outputButton.setEnabled(True)
        self.ui.outputButton.setText('出力')

    # 不正なコマンド設定を確認
    def CommandCheck(self, map):
        if map.end < map.start:
            log.error(f'{map.songname}')
            log.error(f'*end は *start より後ろの位置を指定してください！')
            return False
        return True
   
    # マップ生成＆音声結合
    def output_map(self,output_path):
        # 選択されたレベルのコマンド情報を取得
        map_list = [map for map in self.maps if map is not None]
        song_list = [song for song in self.songs if song is not None]
        n_map = len(map_list)
        for i in range(n_map):
            map = map_list[i]
            song = song_list[i]

            log.debug(f'{map.songname}')

            if not self.CommandCheck(map):
                QMessageBox.warning(None, "コマンドエラー", "コマンドの値が不正です！\nERRORログを確認してください！", QMessageBox.Ok)
                return 0

             # mapのコマンド情報をsongへ渡す
            for com in COMANDS:
                exec('song.'+com+'=map.'+com)

            for com in COMANDS:
                log.debug(f'*{com}:{eval("map."+com)}')

            if self.ui.BMOverwriteCheckAction.isChecked():
                map.CommandOverwrite()


        # 音声処理
        for i in range(n_map):
            song_list[i].speed = map_list[i].bpm2/map_list[i].bpm
        EditSound(song_list)
        newSound = ConcatenateSongs(song_list)

        # マップ処理
        for i in range(n_map):
            map_list[i].speed = song_list[i].speed
            map_list[i].len = song_list[i].len
            map_list[i].postXfade = song_list[i].postXfade
        newMap = NewMap(output_path, map_list)
        newMap.CalcTimeOffset()
        newMap.ConcatenateMaps()

        newMap.sound = newSound

        newMap.OutputMap()
        log.info('マップ出力が完了しました！')

        QMessageBox.information(None, "出力", "出力完了！", QMessageBox.Ok)



if __name__ == '__main__':

    CreateLogFile()
    log = logger(__name__)
    log.info('BeatSaberMapMixer起動')

    #GUI表示
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
    app = QtWidgets.QApplication(sys.argv)
    ui = UI()
    ui.show()
    sys.exit(app.exec())