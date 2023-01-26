from prometheus_client import Counter

import config
from src.log import LoggerMixin
from src.monitoring import MetricsMixin
from src.crawl import CrawlerMixin
from src.transform import TransformerMixin
from src.io import FileInputMixin, ConsoleOutputMixin


class CrawlerProcess(LoggerMixin,
                     MetricsMixin,
                     CrawlerMixin,
                     TransformerMixin,
                     FileInputMixin,
                     ConsoleOutputMixin):

    def __init__(self, file_name):
        self.init_logger()
        self.init_metrics_server()
        self.init_metrics()
        self.init_input(input_file=file_name)
        self.init_output()

        proxy_config = {
            'proxy_type': config.PROXY_TYPE,
            'addr': config.PROXY_ADDRESS,
            'port': config.PROXY_PORT,
        }

        proxy = None
        if config.USE_PROXY:
            proxy = f"{proxy_config['proxy_type']}h://{proxy_config['addr']}:{proxy_config['port']}"

        self.init_telegram(proxy=proxy)

        self.logger.info('PROCESS: INITIALIZED')

    def init_metrics(self):
        self.crawler_counter = Counter(f'cralwed_post',
                                       'Telegram crawler fetched post counter')

    def run(self):
        while True:
            try:
                if self.round_finished():
                    break
                next_ = self.next()
                self.process(next_)
            except KeyboardInterrupt:
                self.logger.warning('PROCESS: KEYBOARD INTERRUPT')
            finally:
                pass

    def process(self, channel):
        self.logger.info(f'PROCESSING {channel}')

        items, publisher_info = self.get_history(channel, limit=config.MAX_POSTS_PER_CHANNEL)
        self.crawler_counter.inc(len(items))
        for item in items:
            if item['type'] == 'album':
                if len(item['album_info']['messages']) > 0:
                    value = self.transform(item['album_info']['messages'],
                                           publisher=publisher_info)
                    self.save(value)
            else:
                value = self.transform([item], publisher=publisher_info)
                self.save(value)
