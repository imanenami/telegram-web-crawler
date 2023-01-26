from src.base import BaseModule

from prometheus_client import start_http_server


class MetricsMixin(BaseModule):
    def init_metrics_server(self,
                            port=9100):
        try:
            start_http_server(port)
            self._log(f'PROMETHEUS: SERVER INITIALIZED ON PORT {port}')
        except OSError:
            self._log(f'PROMETHEUS: SERVER ALREADY RUNNING ON PORT {port}')

    def init_metrics(self):
        pass
