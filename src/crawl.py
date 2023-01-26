from src.base import BaseModule
from src.telegram_web import TelegramWebClient, TelegramWebMessageParser, TelegramWebChannelParser


class CrawlerMixin(BaseModule):

    def init_telegram(self, proxy=None):
        self.telegram_web = TelegramWebClient(proxy=proxy)
        self._log('TELEGRAM WEB: INITIATED')

    def get_history(self, publisher, limit=20):
        user_name = publisher
        messages_list = []
        cursor = None
        publisher_info = None
        while len(messages_list) < limit:
            self._log(f"TELEGRAM WEB: GATHERING MESSAGES FROM {user_name} - CURSOR @ {cursor}")
            try:
                channel_content = self.telegram_web.load_channel_feed(user_name, cursor=cursor)
                channel_parser = TelegramWebChannelParser(content=channel_content)
            except Exception as e:
                self._err(f"TELEGRAM WEB: EXCEPTION {e} OCCURRED"
                          f" WHILE GETTING HISTORY OF {user_name}")
                break
            # publisher info
            if publisher_info is None:
                publisher_info = channel_parser.extract_publisher_info()
            # messages
            for message in channel_parser.extract_messages():
                message_parser = TelegramWebMessageParser(soup=message)
                parsed_message = message_parser.parse()
                parsed_message['channel_id'] = None
                message = self.handle_forwarded_message(
                    self.handle_album_message(parsed_message)
                )
                messages_list.append(message)
            cursor = channel_parser.extract_cursor()

        self._log(f"TELEGRAM WEB: GATHERED {len(messages_list)} MESSAGES FROM {user_name}")

        return messages_list, publisher_info

    def handle_album_message(self, message):
        try:
            if message['album_info']['is_album']:
                album_messages = self.telegram_web.load_multiple_posts(message['album_info']['message_links'])
                message['album_info']['messages'] = list(map(
                    lambda msg: TelegramWebMessageParser(content=msg).parse(), album_messages
                ))
                for album_message in message['album_info']['messages']:
                    album_message['channel_id'] = message['channel_id']
        except Exception as e:
            self._err(f"TELEGRAM WEB: EXCEPTION {e} OCCURRED"
                      f" WHILE GETTING ALBUM MESSAGES OF MESSAGE {message['id']}")
            message["album_info"]["messages"] = []
        return message

    def handle_forwarded_message(self, message):
        try:
            if message["forwarded_info"]:
                message["forwarded_info"]["message"] = dict()
                if message["forwarded_info"]["link"]:
                    fwd_msg = self.telegram_web.load_single_post(message["forwarded_info"]["link"])
                    fwd_msg_parser = TelegramWebMessageParser(content=fwd_msg)
                    message['forwarded_info']['message'] = fwd_msg_parser.parse()
                    message['forwarded_info']['channel_id'] = fwd_msg_parser.extract_channel_id()
                    message['forwarded_info']['publish_datetime'] = \
                        message['forwarded_info']['message']['publish_datetime']
        except Exception as e:
            self._err(f"TELEGRAM WEB: EXCEPTION {e} OCCURRED"
                      f" WHILE GETTING FORWARDED INFO OF MESSAGE {message['id']}")
        return message
