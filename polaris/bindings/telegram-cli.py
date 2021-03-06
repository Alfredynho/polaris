from polaris.types import Message, Conversation, User
from polaris.utils import remove_html, remove_markdown, download
from pytg.receiver import Receiver
from pytg.sender import Sender
from pytg.utils import coroutine
from DictObject import DictObject
import json, logging


class bindings(object):
    def __init__(self, bot):
        self.bot = bot
        self.receiver = Receiver(host="localhost", port=self.bot.config.bindings_token)
        self.sender = Sender(host="localhost", port=self.bot.config.bindings_token)
        logging.getLogger("pytg").setLevel(logging.WARNING)

    def get_me(self):
        msg = self.sender.get_self()
        return User(msg.peer_id, msg.first_name, None, msg.username)

    def convert_message(self, msg):
        id = msg['id']
        if msg.receiver.type == 'user':
            conversation = Conversation(msg.sender.peer_id)
            conversation.title = msg.sender.first_name
        else:
            if msg.receiver.type == 'channel':
                conversation = Conversation(- int('100' + str(msg.receiver.peer_id)))
            else:
                conversation = Conversation(- int(msg.receiver.peer_id))
            conversation.title = msg.receiver.title

        if msg.sender.type == 'user':
            sender = User(int(msg.sender.peer_id))
            sender.first_name = msg.sender.first_name
            if 'first_name' in msg.sender:
                sender.first_name = msg.sender.first_name
            if 'last_name' in msg.sender:
                sender.last_name = msg.sender.last_name
            if 'username' in msg.sender:
                sender.username = msg.sender.username
        else:
            if msg.sender.type == 'channel':
                sender = Conversation(- int('100' + str(msg.sender.peer_id)))
            else:
                sender = Conversation(- int(msg.sender.peer_id))
            sender.title = msg.sender.title

        date = msg.date

        # Gets the type of the message
        if 'text' in msg:
            type = 'text'
            content = msg.text
            extra = None
        elif 'media' in msg:
            type = msg.media.type
            content = msg.id
            if 'caption' in msg.media:
                extra = msg.media.caption
            else:
                extra = None
        elif msg.event == 'service':
            type = 'service'
            if msg.action.type == 'chat_del_user':
                content = 'left_user'
                extra = msg.action.user.peer_id
            elif msg.action.type == 'chat_add_user':
                content = 'join_user'
                extra = msg.action.user.peer_id
            elif msg.action.type == 'chat_add_user_link':
                content = 'join_user'
                extra = msg.sender.peer_id
            else:
                type = None
                content = None
                extra = None
        else:
            type = None
            content = None
            extra = None

        # Generates another message object for the original message if the reply.
        if 'reply_id' in msg:
            reply_msg = self.sender.message_get(msg.reply_id)
            reply = self.convert_message(reply_msg)

        else:
            reply = None

        return Message(id, conversation, sender, content, type, date, reply, extra)

    def receiver_worker(self):
        try:
            logging.debug('Starting receiver worker...')
            while self.bot.started:
                self.receiver.start()
                self.receiver.message(self.main_loop())
        except KeyboardInterrupt:
            pass

    def send_message(self, message):
        if not message.extra:
            message.extra = {}

        if message.type != 'text' and message.content.startswith('http'):
            message.content = download(message.content)
        elif message.type != 'text' and not message.content.startswith('/'):
            message.content = self.sender.load_file(message.content)

        if not message.extra or not 'caption' in message.extra:
            message.extra['caption'] = None

        if message.type == 'text':
            self.sender.send_typing(self.peer(message.conversation.id), 1)

            if 'format' in message.extra and message.extra['format'] == 'Markdown':
                message.content = remove_markdown(message.content)
            elif 'format' in message.extra and message.extra['format'] == 'HTML':
                message.content = remove_html(message.content)

            try:
                self.sender.send_msg(self.peer(message.conversation.id), message.content, enable_preview=False)
            except Exception as e:
                logging.exception(e)

        elif message.type == 'photo':
            self.sender.send_typing(self.peer(message.conversation.id), 1)  # 7
            try:
                if message.reply:
                    self.sender.reply_photo(message.reply, message.content, message.extra['caption'])
                else:
                    self.sender.send_photo(self.peer(message.conversation.id), message.content, message.extra['caption'])
            except Exception as e:
                logging.exception(e)

        elif message.type == 'audio':
            self.sender.send_typing(self.peer(message.conversation.id), 1)  # 6
            try:
                if message.reply:
                    self.sender.reply_audio(message.reply, message.content)
                else:
                    self.sender.send_audio(self.peer(message.conversation.id), message.content)
            except Exception as e:
                logging.exception(e)

        elif message.type == 'document':
            self.sender.send_typing(self.peer(message.conversation.id), 1)  # 8
            try:
                if message.reply:
                    self.sender.reply_document(message.reply, message.content, message.extra['caption'])
                else:
                    self.sender.send_document(self.peer(message.conversation.id), message.content, message.extra['caption'])
            except Exception as e:
                logging.exception(e)

        elif message.type == 'sticker':
            if message.reply:
                self.sender.reply_file(message.reply, message.content)
            else:
                self.sender.send_file(self.peer(message.conversation.id), message.content)

        elif message.type == 'video':
            self.sender.send_typing(self.peer(message.conversation.id), 1)  # 4
            try:
                if message.reply:
                    self.sender.reply_video(message.reply, message.content, message.extra['caption'])
                else:
                    self.sender.send_video(self.peer(message.conversation.id), message.content, message.extra['caption'])
            except Exception as e:
                logging.exception(e)

        elif message.type == 'voice':
            self.sender.send_typing(self.peer(message.conversation.id), 5)
            try:
                if message.reply:
                    self.sender.reply_audio(message.reply, message.content)
                else:
                    self.sender.send_audio(self.peer(message.conversation.id), message.content)
            except Exception as e:
                logging.exception(e)

        elif message.type == 'location':
            self.sender.send_typing(self.peer(message.conversation.id), 1)  # 9
            if message.reply:
                self.sender.reply_location(message.reply, message.content['latitude'], message.content['longitude'])
            else:
                self.sender.send_location(self.peer(message.conversation.id), message.content['latitude'], message.content['longitude'])

        else:
            print('UNKNOWN MESSAGE TYPE: ' + message.type)
            logging.debug("UNKNOWN MESSAGE TYPE")

    @coroutine
    def main_loop(self):
        while self.bot.started:
            msg = (yield)
            if (msg.event == 'message' and msg.own == False) or msg.event == 'service':
                message = self.convert_message(msg)
                self.bot.inbox.put(message)

                try:
                    if message.conversation.id > 0:
                        self.sender.mark_read(self.peer(message.sender.id))
                    else:
                        self.sender.mark_read(self.peer(message.conversation.id))
                except Exception as e:
                    logging.error(e)

    def peer(self, chat_id):
        if chat_id > 0:
            peer = 'user#id' + str(chat_id)
        else:
            if str(chat_id)[1:].startswith('100'):
                peer = 'channel#id' + str(chat_id)[4:]
            else:
                peer = 'chat#id' + str(chat_id)[1:]
        return peer

    def user_id(self, username):
        if username.startswith('@'):
            command = 'resolve_username ' + username[1:]
            resolve = self.sender.raw(command)
            dict = DictObject(json.loads(resolve))
        else:
            dict = self.sender.user_info(username)

        if 'peer_id' in dict:
            return dict.peer_id
        else:
            return False

    def get_id(self, user):
        if isinstance(user, int):
            return user

        if user.isdigit():
            id = int(user)
        else:
            id = int(self.user_id(user))

        return id

    def escape(self, string):
        if string is None:
            return None

        CHARS_UNESCAPED = ["\\", "\n", "\r", "\t", "\b", "\a", "'"]
        CHARS_ESCAPED = ["\\\\", "\\n", "\\r", "\\t", "\\b", "\\a", "\\'"]

        for i in range(0, 7):
            string = string.replace(CHARS_UNESCAPED[i], CHARS_ESCAPED[i])
        return string.join(["'", "'"])  # wrap with single quotes.
