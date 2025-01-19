import logging
import os.path
from datetime import datetime
from logging import getLoggerClass, Logger, INFO

__all__ = ('MyLogger', 'logger')

class MyLogger(getLoggerClass()):
    def __init__(self) -> None:
        self.filepath = f'logs/{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}.txt'
        if not os.path.exists(self.filepath):
            open(self.filepath, 'x').close() # create empty file
        super().__init__('my_logger', INFO)

    def log(self, level: int, msg: str, *args, **kwargs) -> None:
        print(msg)
        with open(self.filepath, 'a', encoding='utf-8') as f:
            level_text = {v: i for i, v in logging.getLevelNamesMapping().items()}[level]
            f.write(f'[{level_text} {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}] {msg}\n')
        return super().log(level, msg, *args, **kwargs)

logger = MyLogger()
