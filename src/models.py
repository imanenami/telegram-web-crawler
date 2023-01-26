import dataclasses
import re
import enum
from datetime import datetime
from dataclasses import dataclass, field


class BaseEnum(enum.Enum):
    @classmethod
    def choices(cls):
        return tuple((int(i.value), i.name) for i in cls)


class MessageType(BaseEnum):
    VIDEO = "VIDEO"
    PHOTO = "PHOTO"
    AUDIO = "AUDIO"
    POLL = "POLL"
    TEXT = "TEXT"
    ALBUM = "ALBUM"


def parse_text_hashtags(text):
    try:
        return re.findall(r'#(\w+)', text)
    except Exception:
        return []


def serialize(obj: dataclasses.dataclass, ret: dict):
    for k in obj.__dataclass_fields__:
        v = getattr(obj, k)
        if isinstance(v, datetime):
            s = v.isoformat()
        # album_messages is a list of PostInfo and should be explicitly handled
        elif k == "album_messages" and v is not None:
            s = []
            for message in v:
                tmp = dict()
                serialize(message, tmp)
                s.append(tmp)
        elif isinstance(v, str) or isinstance(v, dict) or isinstance(v, list) \
          or isinstance(v, float) or isinstance(v, int) or v is None:
            s = v
        else:
            s = v.__dict__
        ret[k] = s
    return ret


@dataclass(init=True, repr=True)
class PublisherInfo:
    link: str = None
    channel_id: str = None
    author: str = None
    title: str = None
    username: str = None


@dataclass(init=True, repr=True)
class ForwardedInfo:
    publish_datetime: datetime = None
    user_id: str = None
    channel_id: str = None
    message_id: int = None


@dataclass(init=True, repr=True)
class AudioInfo:
    duration: float = None
    title: str = None
    performer: str = None

    def format_audio_info(self, obj):
        attributes = obj['audio_info']
        self.title = attributes['title']
        self.performer = attributes['performer']


@dataclass(init=True, repr=True)
class PollInfo:
    poll_id: int = None
    total_voters: int = None
    question: str = None
    is_quiz: bool = False
    answers: list = field(default_factory=list)

    def format_poll_info(self, obj):
        attributes = obj['poll_info']
        self.total_voters = attributes['voters']
        self.question = attributes['question']
        self.is_quiz = attributes['is_quiz']
        for i, answer in enumerate(attributes['options']):
            self.answers.append({
                "option": str(i),
                "text": answer
            })


@dataclass(init=True, repr=True)
class PhotoInfo:
    width: int = None
    height: int = None
    url: str = None

    def format_photo_info(self, obj):
        self.width = obj['photo_info']['width']
        self.height = obj['photo_info']['height']
        self.url = obj['photo_info']['url']


@dataclass(init=True, repr=True)
class VideoInfo:
    duration: float = None
    width: int = None
    height: int = None
    url: str = None
    thumb_url: str = None

    def format_video_info(self, obj):
        document = obj['video_info']
        self.duration = document['duration']
        self.width = document['width']
        self.height = document['height']
        self.url = document['url']
        self.thumb_url = document['thumb_url']


@dataclass(init=True, repr=True)
class PostInfo:
    type: str = None
    message_id: int = None
    text: str = None
    hashtags: list = field(default_factory=list)
    views: int = None
    publish_datetime: datetime = None
    link: str = None
    reply_to: int = None
    publisher_info: PublisherInfo = None
    forwarded_info: ForwardedInfo = None
    photo_info: PhotoInfo = None
    video_info: VideoInfo = None
    audio_info: AudioInfo = None
    poll_info: PollInfo = None
    album_messages: list = field(default_factory=list)

    def format_post_info(self,
                         obj,
                         publisher=None,
                         post_type=None,
                         text=None):
        self.views = obj['views']
        self.publish_datetime = obj['publish_datetime']
        self.link = obj['link']
        self.publisher_info = PublisherInfo()
        self.publisher_info.link = f"https://t.me/{obj['channel']}"
        self.publisher_info.channel_id = obj['channel_id']
        self.publisher_info.author = obj['author']

        if publisher is not None:
            self.publisher_info.title = publisher['title']
            self.publisher_info.username = obj['channel']

        if post_type != MessageType.ALBUM.value:
            self.message_id = obj['id']
            self.text = obj['text']
            self.hashtags = parse_text_hashtags(obj['text'])
        else:
            self.message_id = obj['publish_timestamp']
            self.text = text
            self.hashtags = parse_text_hashtags(text)

        if obj['forwarded_info'] is not None:
            self.forwarded_info = ForwardedInfo()
            fwd_datetime = obj['forwarded_info'].get('publish_datetime', None)
            if fwd_datetime is not None:
                self.forwarded_info.publish_datetime = fwd_datetime.isoformat()
            self.forwarded_info.user_id = obj['forwarded_info'].get('user_id', None)
            self.forwarded_info.channel_id = obj['forwarded_info'].get('channel_id', None)
            self.forwarded_info.message_id = obj['forwarded_info'].get('message_id', None)

        if obj['reply_to'] is not None:
            self.reply_to = obj['reply_to']
