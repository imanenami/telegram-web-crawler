import logging


class BaseModule(object):

    def _log(self, msg, level=logging.INFO):
        if getattr(self, "logger", None) is not None:
            self.logger.log(level, msg)
        else:
            print(msg)

    def _err(self, msg):
        self._log(msg, logging.ERROR)
