import json

from src.base import BaseModule
from src.models import serialize


class InputInterface(BaseModule):

    def init_input(self, *args, **kwargs):
        raise NotImplementedError()

    def next(self):
        raise NotImplementedError()

    def round_finished(self):
        raise NotImplementedError()


class OutputInterface(BaseModule):

    def init_output(self, *args, **kwargs):
        raise NotImplementedError()

    def save(self, value):
        raise NotImplementedError()


class FileInputMixin(InputInterface):

    def init_input(self, *args, **kwargs):
        input_file = kwargs.get("input_file")
        raw = open(input_file).readlines()
        self.file_input_list = [l.replace("\n", "").replace("\r", "").replace(" ", "") for l in raw]
        self.file_input_index = 0

    def next(self):
        _next = self.file_input_list[self.file_input_index]
        self.file_input_index += 1
        return _next

    def round_finished(self):
        return self.file_input_index == len(self.file_input_list)


class ConsoleOutputMixin(OutputInterface):

    def init_output(self, *args, **kwargs):
        pass

    def save(self, value):
        serialized = dict()
        serialize(value, serialized)
        json_ = json.dumps(serialized)
        self._log(json_)
