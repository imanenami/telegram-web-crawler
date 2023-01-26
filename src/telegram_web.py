import re
import json
import requests
import datetime
import calendar
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor


USER_AGENT = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:94.0) Gecko/20100101 Firefox/94.0"
REQUEST_TIMEOUT = 5


class TelegramWebBaseException(Exception):
    """
    Raise for errors due to telegram web scraping
    """


class TelegramWebClient:
    def __init__(self, proxy=None):
        self.proxies = None
        if proxy:
            self.proxies = dict(http=proxy, https=proxy)
        self.user_agent = USER_AGENT
        self.headers = {'User-Agent': self.user_agent}
        self.logger = print

    def _log(self, msg):
        self.logger(msg)

    def _req(self, url, max_retries=1, xhr_post=False, stream=False):
        retries = 0
        while retries < max_retries:
            try:
                if not xhr_post:
                    response = requests.get(url,
                                            headers=self.headers,
                                            proxies=self.proxies,
                                            timeout=REQUEST_TIMEOUT,
                                            stream=stream)
                else:
                    headers = self.headers.copy()
                    headers['X-Requested-With'] = 'XMLHttpRequest'
                    response = requests.post(url,
                                             headers=headers,
                                             proxies=self.proxies,
                                             timeout=REQUEST_TIMEOUT)
                return response
            except requests.exceptions.Timeout:
                self._log("TELEGRAM WEB - REQUEST TIMEOUT ERROR")
            except requests.exceptions.ProxyError:
                self._log("TELEGRAM WEB - PROXY ERROR")
            except requests.exceptions.SSLError:
                self._log("TELEGRAM WEB - SSL ERROR")
            except requests.exceptions.ConnectionError:
                self._log("TELEGRAM WEB - CONNECTION ERROR")
            except json.JSONDecodeError:
                self._log("TELEGRAM WEB - JSON DECODE ERROR")
            except Exception as e:
                self._log(f"TELEGRAM WEB - UNKNOWN ERROR - {e}")
            retries += 1
        return None

    def _channel_load_main(self, channel):
        url = f"https://t.me/s/{channel}"
        response = self._req(url)
        if response and response.url == url:
            return response.text
        else:
            return None

    def _channel_load_more(self, cursor):
        url = f"https://t.me{cursor}"
        response = self._req(url, xhr_post=True)
        return response.json()

    def load_channel_feed(self, channel, cursor=None):
        if cursor:
            return self._channel_load_more(cursor)
        else:
            return self._channel_load_main(channel)

    def load_single_post(self, post_url):
        url = f"{post_url}?embed=1&single=1"
        response = self._req(url)
        return response.text

    def load_multiple_posts(self, post_urls):
        thread_pool = ThreadPoolExecutor()
        results = list(thread_pool.map(self.load_single_post, post_urls))
        thread_pool.shutdown(wait=True)
        return results


class TelegramWebParserHelpers:
    @staticmethod
    def extract_channel_and_message_id(link: str):
        parsed_link = urlparse(link).path
        exd = parsed_link.split('/')
        return exd[-2], int(exd[-1])

    @staticmethod
    def convert_shorthand_to_number(text: str):
        text = text.lower()
        if 'k' in text:
            return int(float(text.strip('k')) * 1000)
        elif 'm' in text:
            return int(float(text.strip('m')) * 1000000)
        else:
            return int(text)

    @staticmethod
    def convert_duration_str_to_seconds(duration: str):
        unit = 1
        seconds = 0
        for val in duration.split(":")[::-1]:
            seconds += int(val) * unit
            unit *= 60
        return seconds


class TelegramWebChannelParser(TelegramWebParserHelpers):
    def __init__(self, content: str = None, soup: BeautifulSoup = None):
        if soup:
            self.soup = soup
        elif content:
            self.soup = BeautifulSoup(content, "html.parser")
        else:
            raise ValueError("No valid input provided to the parser")

    def extract_messages(self):
        messages_soup = self.soup.findAll('div', {'class': 'tgme_widget_message_wrap'})
        return messages_soup

    def extract_publisher_info(self):
        publisher_info = dict(
            avatar_url=None,
            title=None,
            user_name=None,
            subscribers_count=0,
            photos_count=0,
            videos_count=0,
            files_count=0,
            links_count=0,
            description=None
        )
        channel_info = self.soup.find('div', {'class': 'tgme_channel_info'})
        if channel_info:
            if channel_info.find('img'):
                publisher_info['avatar_url'] = channel_info.find('img')['src']

            if channel_info.find('div', {'class': 'tgme_channel_info_header_title'}):
                publisher_info['title'] = channel_info.find(
                    'div', {'class': 'tgme_channel_info_header_title'}
                ).text

            if channel_info.find('div', {'class': 'tgme_channel_info_header_username'}):
                publisher_info['user_name'] = channel_info.find(
                    'div', {'class': 'tgme_channel_info_header_username'}
                ).text.replace('@', '')

            for counter in channel_info.findAll('div', {'class': 'tgme_channel_info_counter'}):
                counter_type = counter.find('span', {'class': 'counter_type'}).text.lower()
                counter_value = self.convert_shorthand_to_number(
                    counter.find('span', {'class': 'counter_value'}).text
                )
                try:
                    publisher_info[f'{counter_type}_count'] = counter_value
                except KeyError:
                    pass

            if channel_info.find('div', {'class': 'tgme_channel_info_description'}):
                txt_html = channel_info.find('div', {'class': 'tgme_channel_info_description'})
                for br in txt_html.findAll('br'):
                    br.replaceWith('\n')
                publisher_info['description'] = txt_html.text
            else:
                publisher_info['description'] = None

            return publisher_info
        else:
            return None

    def extract_cursor(self):
        if self.soup.find('link', {'rel': 'prev'}):
            return self.soup.find('link', {'rel': 'prev'})['href']
        elif self.soup.find('a', {'class': 'tme_messages_more'}):
            return self.soup.find('a', {'class': 'tme_messages_more'})['href']
        else:
            return None


class TelegramWebMessageParser(TelegramWebParserHelpers):
    def __init__(self, content: str = None, soup: BeautifulSoup = None):
        if soup:
            self.soup = soup
        elif content:
            self.soup = BeautifulSoup(content, "html.parser")
        else:
            raise ValueError("No valid input provided to the parser")

    def parse(self):
        generic_info = self.extract_generic_info()
        if generic_info['album_info']["is_album"]:
            generic_info['type'] = 'album'
            return generic_info
        if self.extract_poll_info():
            generic_info['type'] = 'poll'
            generic_info['poll_info'] = self.extract_poll_info().copy()
        elif self.extract_audio_info():
            generic_info['type'] = 'audio'
            generic_info['audio_info'] = self.extract_audio_info().copy()
        elif self.extract_video_info():
            generic_info['type'] = 'video'
            generic_info['video_info'] = self.extract_video_info().copy()
        elif self.extract_photo_info():
            generic_info['type'] = 'photo'
            generic_info['photo_info'] = self.extract_photo_info().copy()
        else:
            generic_info['type'] = 'text'
        return generic_info

    def extract_generic_info(self):
        link = self.soup.find('a', {'class': 'tgme_widget_message_date'})
        if link:
            link = link['href'].split('?')[0]
            channel, message_id = self.extract_channel_and_message_id(link)
        else:
            channel, message_id = None, None

        if self.soup.find('span', {'class': 'tgme_widget_message_views'}):
            views = self.convert_shorthand_to_number(
                self.soup.find('span', {'class': 'tgme_widget_message_views'}).text
            )
        else:
            views = 0

        if self.soup.find('time'):
            publish_datetime = datetime.datetime.strptime(
                self.soup.findAll('time')[-1]['datetime'], '%Y-%m-%dT%H:%M:%S%z'
            )
            publish_timestamp = calendar.timegm(publish_datetime.timetuple())
        else:
            publish_timestamp = None
            publish_datetime = None

        if self.soup.find('div', {'class': 'tgme_widget_message_text'}):
            txt_html = self.soup.find('div', {'class': 'tgme_widget_message_text'})
            for br in txt_html.findAll('br'):
                br.replaceWith('\n')
            txt_content = txt_html.text
        else:
            txt_content = None

        if self.soup.find('span', {'class': 'tgme_widget_message_from_author'}):
            author = self.soup.find('span', {'class': 'tgme_widget_message_from_author'}).text
        else:
            author = None

        if self.soup.find('a', {'class': 'tgme_widget_message_reply'}):
            link = self.soup.find('a', {'class': 'tgme_widget_message_reply'})['href']
            _, reply_to = self.extract_channel_and_message_id(link)
        else:
            reply_to = None

        return dict(
            channel=channel,
            link=link,
            id=message_id,
            views=views,
            publish_datetime=publish_datetime,
            publish_timestamp=publish_timestamp,
            text=txt_content,
            album_info=self.extract_album_info(),
            forwarded_info=self.extract_forwarded_from_info(),
            author=author,
            reply_to=reply_to,
            replies=None
        )

    def extract_album_info(self):
        album_info = dict(
            is_album=False,
            message_links=[]
        )
        if self.soup.find('div', {'class': 'tgme_widget_message_grouped_wrap'}):
            album_info['is_album'] = True
            for item in self.soup.findAll('a', {'class': 'grouped_media_wrap'}):
                album_info["message_links"].append(item['href'].replace('?single', ''))
        return album_info

    def extract_photo_info(self):
        photo = self.soup.find("a", {"class": "tgme_widget_message_photo_wrap"})
        photo_info = dict(
            width=None,
            height=None,
            url=None,
        )
        if photo is not None:
            try:
                photo_width = re.findall('width:([0-9]+)', photo.get("style"))[0]
                photo_info["width"] = int(photo_width)

                photo_wrapper = photo.find('div', {'class': 'tgme_widget_message_photo'})
                photo_size_ratio = re.findall('padding-top:([.0-9]+)', photo_wrapper.get("style"))[0]
                photo_info["height"] = int(photo_info["width"] * float(photo_size_ratio) / 100)
            except Exception:
                pass

            photo_url = re.findall("background-image:.?url.'(.+?)'.", photo.get("style"))[0]
            photo_info["url"] = photo_url

            return photo_info
        else:
            return None

    def extract_video_info(self):
        video_div = self.soup.find("div", {"class": "tgme_widget_message_video_wrap"})
        video_info = dict(
            duration=0,
            width=None,
            height=None,
            file_name=None,
            url=None,
            thumb_url=None
        )
        if video_div is not None:
            try:
                video_width = re.findall('width:([0-9]+)', video_div.get("style"))[0]
                video_info["width"] = int(video_width)

                video_size_ratio = re.findall('padding-top:([.0-9]+)', video_div.get("style"))[0]
                video_info["height"] = int(video_info["width"] * float(video_size_ratio) / 100)
            except Exception:
                pass

            thumb_soup = self.soup.find("i", {"class": "tgme_widget_message_video_thumb"})
            if thumb_soup:
                try:
                    thumb_url = re.findall("background-image:.?url.'(.+?)'.", thumb_soup.get("style"))[0]
                    video_info["thumb_url"] = thumb_url
                except Exception:
                    pass

            if self.soup.find('time', {'class': 'message_video_duration'}):
                video_info['duration'] = self.convert_duration_str_to_seconds(
                    self.soup.find('time', {'class': 'message_video_duration'}).text
                )

            if video_div.find('video'):
                video_url = video_div.find('video')['src']
                video_info["url"] = video_url

            return video_info
        else:
            return None

    def extract_audio_info(self):
        audio_info = dict(
            duration=None,
            title=None,
            performer=None,
            file_name=None,
            url=None
        )
        if self.soup.find('div', {'class': 'tgme_widget_message_document_icon accent_bg audio'}):
            if self.soup.find('div', {'class': 'tgme_widget_message_document_title'}):
                audio_info['title'] = self.soup.find(
                    'div', {'class': 'tgme_widget_message_document_title'}
                ).text
            if self.soup.find('div', {'class': 'tgme_widget_message_document_extra'}):
                audio_info['performer'] = self.soup.find(
                    'div', {'class': 'tgme_widget_message_document_extra'}
                ).text
            return audio_info
        else:
            return None

    def extract_poll_info(self):
        poll_info = dict(
            voters=0,
            question=None,
            options=[],
            is_quiz=None
        )
        if self.soup.find('div', {'class': 'tgme_widget_message_poll'}):

            if self.soup.find('span', {'class': 'tgme_widget_message_voters'}):
                poll_info['voters'] = self.convert_shorthand_to_number(
                    self.soup.find('span', {'class': 'tgme_widget_message_voters'}).text
                )

            if self.soup.find('div', {'class': 'tgme_widget_message_poll_question'}):
                poll_info['question'] = self.soup.find(
                    'div', {'class': 'tgme_widget_message_poll_question'}
                ).text

            for option in self.soup.findAll('div', {'class': 'tgme_widget_message_poll_option'}):
                poll_info['options'].append(
                    option.find('div', {'class': 'tgme_widget_message_poll_option_text'}).text
                )

            if self.soup.find('div', {'class': 'tgme_widget_message_poll_type'}):
                if "quiz" in self.soup.find('div', {'class': 'tgme_widget_message_poll_type'}).text.lower():
                    poll_info['is_quiz'] = True
                else:
                    poll_info['is_quiz'] = False

            return poll_info
        else:
            return None

    def extract_forwarded_from_info(self):
        forwarded_header = dict(
            channel=None,
            user_name=None,
            channel_id=None,
            message_id=None,
            link=None,
            publish_datetime=None
        )
        forwarded_from = self.soup.find('div', {'class': 'tgme_widget_message_forwarded_from'})
        if forwarded_from is not None:
            # extract user/channel name
            try:
                forwarded_header["user_name"] = forwarded_from.find(
                    "span", {"class": "tgme_widget_message_forwarded_from_name"}
                ).text
            except AttributeError:
                forwarded_header["user_name"] = forwarded_from.find(
                    "a", {"class": "tgme_widget_message_forwarded_from_name"}
                ).text
            # extract original message link, channel & message id
            try:
                forwarded_header["link"] = forwarded_from.find('a')['href'].split('?')[0]
                forwarded_header["channel"], forwarded_header["message_id"] = \
                    self.extract_channel_and_message_id(str(forwarded_header["link"]))
            except Exception:
                pass
            return forwarded_header
        else:
            return None

    def extract_channel_id(self):
        try:
            data_peer = self.soup.find("div", {"class": "tgme_widget_message"})["data-peer"]
            channel_id = data_peer.split("_")[0][1:]
        except Exception:
            channel_id = None
        return channel_id
