from src.models import *


class TransformerMixin:

    def _get_message_type(self, obj, data):
        if obj['type'] == 'video':
            data.type = MessageType.VIDEO.value
            data.video_info = VideoInfo()
            data.video_info.format_video_info(obj)
        elif obj['type'] == 'photo':
            data.type = MessageType.PHOTO.value
            data.photo_info = PhotoInfo()
            data.photo_info.format_photo_info(obj)
        elif obj['type'] == 'audio':
            data.type = MessageType.AUDIO.value
            data.audio_info = AudioInfo()
            data.audio_info.format_audio_info(obj)
        elif obj['type'] == 'poll':
            data.type = MessageType.POLL.value
            data.poll_info = PollInfo()
            data.poll_info.format_poll_info(obj)
        else:
            data.type = MessageType.TEXT.value
        return data

    def get_album_messages(self, objects):
        album_messages = []

        for obj in objects:
            album_message = PostInfo()
            album_message.message_id = obj['id']
            album_message.text = obj['text']
            album_message.hashtags = parse_text_hashtags(obj['text'])
            album_message = self._get_message_type(obj=obj, data=album_message)
            album_messages.append(album_message)

        return album_messages

    def transform(self, objects, publisher=None):
        data = PostInfo()

        if len(objects) == 1:
            data.format_post_info(objects[0], publisher=publisher)
            data = self._get_message_type(obj=objects[0], data=data)
        else:
            text = "".join(obj['text'] for obj in objects if obj['text'])
            data.format_post_info(objects[0], post_type=MessageType.ALBUM.value, text=text,
                                  publisher=publisher)
            data.type = MessageType.ALBUM.value
            data.album_messages = self.get_album_messages(objects)

        return data
