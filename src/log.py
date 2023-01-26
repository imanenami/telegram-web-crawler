import sys
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pytz import timezone

import config


class ProcessLogger(object):
    def __init__(self, level=logging.INFO):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(level)
        logging.Formatter.converter = self.custom_time

    @property
    def logger_formatter(self):
        return logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def add_file_handler(self, filename='process.log'):
        file_handler = logging.FileHandler(filename)
        file_handler.setFormatter(self.logger_formatter)
        self.logger.addHandler(file_handler)

        return self

    def add_rotating_file_handler(self,
                                  filename='process.log',
                                  max_bytes=50*1024*1024,
                                  backup_count=3):
        rotating_file_handler = RotatingFileHandler(filename,
                                                    maxBytes=max_bytes,
                                                    backupCount=backup_count)
        rotating_file_handler.setFormatter(self.logger_formatter)
        self.logger.addHandler(rotating_file_handler)

        return self

    def add_time_rotating_file_handler(self,
                                       filename='process.log',
                                       when='D',
                                       interval=1,
                                       backupCount=7,
                                       encoding='utf-8',
                                       delay=False,
                                       utc=True):
        time_rotating_file_handler = logging.handlers.TimedRotatingFileHandler(filename=filename,
                                                                               when=when,
                                                                               interval=interval,
                                                                               backupCount=backupCount,
                                                                               encoding=encoding,
                                                                               delay=delay,
                                                                               utc=utc)
        time_rotating_file_handler.setFormatter(self.logger_formatter)
        self.logger.addHandler(time_rotating_file_handler)

        return self

    def add_stdout_handler(self):
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(self.logger_formatter)
        self.logger.addHandler(stdout_handler)

        return self

    @staticmethod
    def custom_time(*args):
        tz = timezone(config.TIMEZONE)
        converted = datetime.now(tz=tz)
        return converted.timetuple()


class LoggerMixin(ProcessLogger):

    def init_logger(self):
        super().__init__()
        if not self.logger.hasHandlers():
            self.add_rotating_file_handler(filename='process.log',
                                           max_bytes=2000000,
                                           backup_count=5
                                           )
            self.add_stdout_handler()

        self.logger.info('LOGGER: INITIALIZED')
