import io
import os.path
from datetime import datetime

__all__ = ('Logger', 'logger')

class Logger(io.FileIO):
    def __init__(self):
        if not os.path.exists('./logs'):
            os.mkdir('./logs')
        self.path = f'logs/{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}.txt'
        if not os.path.exists(self.path):
            open(self.path, 'x').close() # create empty file
        super().__init__(file=self.path, mode='a')

    def write(self, msg: str, /):
        mtp = f'[{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}] {msg}'
        print(mtp, end='')
        return super().write(mtp.encode('utf-8'))

    def __del__(self):
        return self.close()

logger = Logger()
