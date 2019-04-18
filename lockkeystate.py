import re
import threading
import time

LOCK_KEYS = ['Caps', 'Num', 'Scroll']

class LockKeyState:

    def __init__(self, connection, interval=0.2, onchange=None):
        self.connection = connection
        self.interval = interval
        self.onchange = onchange
        self.keys = {k: None for k in LOCK_KEYS}
        thread = threading.Thread(target=self.run)
        thread.daemon = True
        thread.start()

    def run(self):
        while True:
            x = self.connection.run('DISPLAY=:0 xset q', hide=True)
            keys = {}
            for k in LOCK_KEYS:
                m = re.search(k + r'\s*Lock:\s*(on|off)', x.stdout)
                if m:
                    keys[k] = m.group(1) == 'on'
                else:
                    keys[k] = None
            if keys != self.keys:
                self.keys = keys
                if self.onchange:
                    self.onchange(keys)
            time.sleep(self.interval)
