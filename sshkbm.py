#!/usr/bin/env python3

import shlex
import sys
from fabric import Connection
from math import atan, copysign, pi
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QShortcut
from PyQt5.QtCore import QObject, pyqtSlot, QEvent, Qt
from PyQt5.QtGui import QKeySequence
from ui.sshkbm_window import Ui_SSHKBMWindow
from util import characters

CIRCLE_R1 = 0.21
CIRCLE_R2 = 0.51
CIRCLE_R3 = 0.98

class SSHKBM(QObject):

    def __init__(self, args):
        super().__init__()
        self.connection = None
        self.conn_params = {p: None for p in ('host', 'user', 'port', 'password')}
        self.display = None
        # Initialise UI
        self.app = QApplication(sys.argv)
        self.window = QMainWindow()
        self.ui = Ui_SSHKBMWindow()
        self.ui.setupUi(self.window)
        self.on_disconnect()
        # Bind events
        self.ui.connectButton.clicked.connect(self.click_connect)
        self.ui.connectButton.setShortcut('Return')
        self.ui.sendTextButton.clicked.connect(self.click_send_text)
        QShortcut(QKeySequence('Ctrl+Return'),
            self.ui.typingField,
            activated=self.click_send_text)
        orig_evt = self.ui.keyboardTab.keyPressEvent
        def new_evt(evt):
            self.keyboard_key_pressed(evt.key(), evt.modifiers())
            orig_evt(evt)
        self.ui.keyboardTab.keyPressEvent = new_evt
        key_buttons = [b + 'Btn' for b in
            [d + 'Arrow' for d in ['up', 'down', 'left', 'right']] +
            ['f' + str(n) for n in range(1, 12)] +
            ['tab', 'caps', 'num', 'scroll',
             'ins', 'del', 'prtscr', 'pgup', 'pgdn', 'home', 'end', 'esc',
             'volUp', 'volDown', 'mute', 'play', 'stop', 'prev', 'next', 'space']]
        btn_clk = lambda b: lambda: self.keyboard_key_pressed(\
                                QObject.property(getattr(self.ui, b), 'Key'), 0)
        for b in key_buttons:
            getattr(self.ui, b).clicked.connect(btn_clk(b))
        self.mp = self.ui.mousePicture
        def new_evt(evt):
            self.mouse_cmd(evt.pos())
        self.mp.mousePressEvent = new_evt
        # Fill in default values
        self.ui.hostField.setText(args.get('host', ''))
        self.ui.portField.setText(args.get('port', ''))
        self.ui.userField.setText(args.get('user', ''))
        self.ui.passwordField.setText(args.get('password', ''))
        self.ui.displayField.setText(args.get('display', ''))
        # Finally, show the window
        self.window.show()
        if args.get('connect', False):
            self.click_connect()
        self.app.exec_()

    def on_connect(self, connect=True):
        for i in range(1, 4):
            self.ui.tabWidget.setTabEnabled(i, connect)
        for e in [self.ui.hostField, self.ui.portField, self.ui.userField,
                    self.ui.passwordField]:
            e.setEnabled(not connect)
        self.ui.statusbar.showMessage('Connected.' if connect else 'Disconnected.')
        self.ui.connectButton.setText('Connect' if not connect else 'Disconnect')

    def on_disconnect(self):
        self.on_connect(False)

    def _get_connection_params(self):
        none_if_empty = lambda s : s if s else None
        self.conn_params.update({
            'host': none_if_empty(str(self.ui.hostField.text()).strip()),
            'port': none_if_empty(str(self.ui.portField.text())),
            'user': none_if_empty(str(self.ui.userField.text())),
            'password': none_if_empty(str(self.ui.passwordField.text()))
        })

    @pyqtSlot()
    def click_connect(self):
        if self.connection is not None and self.connection.is_connected:
            self.connection.close()
            self.on_connect(self.connection.is_connected)
            return
        self._get_connection_params()
        k = None
        if self.conn_params['password'] is not None:
            k = {'password': self.conn_params['password']}
        if self.conn_params['host'] is None:
            QMessageBox.critical(self.ui.centralwidget, 'Error',
                        'Please fill in the host.', QMessageBox.Ok)
            return
        self.connection = Connection(
            self.conn_params['host'],
            port=self.conn_params['port'],
            user=self.conn_params['user'],
            connect_kwargs = k,
        )
        self.connection.open()
        self.on_connect(self.connection.is_connected)

    @pyqtSlot()
    def click_send_text(self):
        text = str(self.ui.typingField.toPlainText())
        display = str(self.ui.displayField.text())
        cmd = 'DISPLAY=' + shlex.quote(display) + ' '
        cmd += 'xdotool type '
        cmd += shlex.quote(text).replace('\n', '\r')
        self.connection.run(cmd)
        self.ui.typingField.setPlainText('')

    def keyboard_key_pressed(self, key, modifiers):
        if type(key) == int:
            if 0x1001250 <= key <= 0x1001262:
                name = characters.DEAD[key]
            elif 0x41 <= key <= 0x5a or 0x61 <= key <= 0x7a:
                name = chr(key)
            else:
                name = QKeySequence(key).toString()
            try:
                name.encode('utf-8')
            except UnicodeEncodeError:
                return
        else:
            name = key
        k = []
        if self.ui.ignoreModifiersCheck.isChecked():
            modifiers = 0x0
        if modifiers & Qt.KeypadModifier:
            name = 'KP_' + name
        if self.ui.composeCheck.isChecked():
            k.append('Multi_key')
        if self.ui.ctrlCheck.isChecked() or (modifiers & Qt.ControlModifier):
            k.append('Ctrl')
        if self.ui.shiftCheck.isChecked() or (modifiers & Qt.ShiftModifier):
            k.append('Shift')
        if self.ui.altCheck.isChecked() or (modifiers & Qt.AltModifier):
            k.append('Alt')
        if self.ui.superCheck.isChecked() or (modifiers & Qt.MetaModifier):
            k.append('Super')
        if self.ui.altGrCheck.isChecked():
            k.append('ISO_Level3_Shift')
        if name in characters.CHARACTERS:
            name = characters.CHARACTERS[name]
        if len(name) == 1:
            name = name.lower()
        k.append(name)
        key_str = '+'.join(k)
        self.ui.lastKeyTitleLabel.setText('Last key sent:')
        self.ui.lastKeyLabel.setText(key_str)
        display = str(self.ui.displayField.text())
        cmd = 'DISPLAY=' + shlex.quote(display) + ' '
        cmd += 'xdotool key ' + shlex.quote(key_str)
        self.connection.run(cmd)

    def mouse_cmd(self, pos):
        x =  (2 * pos.x() / self.mp.width()  - 1)
        y = (-2 * pos.y() / self.mp.height() + 1)
        r = (x ** 2 + y ** 2) ** .5
        theta = atan(y / x if x != 0 else copysign(float('inf'), y)) * 180 / pi
        if r > CIRCLE_R3:
            # Outside circle, do nothing
            return
        elif r > CIRCLE_R2:
            # Move
            dr = round((r - CIRCLE_R2) / (CIRCLE_R3 - CIRCLE_R2) * 400)
            dtheta = round(90 - theta) + (0 if x > 0 else 180)
            cmd = 'mousemove_relative --polar ' + str(dtheta) + ' ' + str(dr)
        elif r > CIRCLE_R1:
            if abs(theta) < 60:
                if x >= 0:
                    # Right click
                    cmd = 'click 3'
                else:
                    # Left click
                    cmd = 'click 1'
            else:
                if y >= 0:
                    # Scroll up
                    cmd = 'click 4'
                else:
                    # Scroll down
                    cmd = 'click 5'
        else:
            # Middle click
            cmd = 'click 2'
        display = str(self.ui.displayField.text())
        cmd = 'DISPLAY=' + shlex.quote(display) + ' xdotool ' + cmd
        self.connection.run(cmd)
        self.ui.typingField.setPlainText('')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Send keyboard and mouse events over SSH')
    parser.add_argument('--host', '-H', default='')
    parser.add_argument('--port', '-P', default='22')
    parser.add_argument('--user', '-u', default='')
    parser.add_argument('--password', '-p', default='')
    parser.add_argument('--display', '-d', default=':0')
    parser.add_argument('--connect', '-c', action='store_true')
    args = vars(parser.parse_args())
    SSHKBM(args)




