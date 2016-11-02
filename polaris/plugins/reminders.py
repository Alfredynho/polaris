from polaris.utils import get_input, first_word, all_but_first_word, is_int
from polaris.types import AutosaveDict, Message, Conversation
from collections import OrderedDict
from DictObject import DictObject
from threading import Thread
from time import time, sleep

class plugin(object):
    # Loads the text strings from the bots language #

    def __init__(self, bot):
        self.bot = bot
        self.commands = self.bot.trans.plugins.reminders.commands
        self.description = self.bot.trans.plugins.reminders.description
        self.reminders = AutosaveDict('polaris/data/%s.reminders.json' % self.bot.name)
        self.sort_reminders()
        #d = Thread(target=self.daemon)
        #d.daemon = True
        #d.start()


    # Plugin action #
    def run(self, m):
        input = get_input(m, ignore_reply=False)
        if not input:
            return self.bot.send_message(m, self.bot.trans.errors.missing_parameter, extra={'format': 'HTML'})

        # Lists all pins #
        delay = first_word(input)
        if delay:
            delaytime = delay[:-1]
            unit = delay[-1:]
            if not is_int(delaytime) or is_int(unit):
                return self.bot.send_message(m, self.bot.trans.plugins.reminders.strings.wrongdelay)

        alarm = time() + self.to_seconds(delaytime, unit)

        text = all_but_first_word(input)
        if not text:
            return self.bot.send_message(m, self.bot.trans.plugins.reminders.strings.noreminder)

        reminder = DictObject(OrderedDict())
        reminder.id = '%s:%s' % (m.sender.id, time())
        reminder.alarm = alarm
        reminder.chat_id = m.conversation.id
        reminder.text = text
        reminder.first_name = m.sender.first_name
        reminder.username = m.sender.username

        self.reminders.list.append(reminder)
        self.sort_reminders()

        if unit == 's':
            delay = delay.replace('s', ' seconds')
        if unit == 'm':
            delay = delay.replace('m', ' minutes')
        if unit == 'h':
            delay = delay.replace('h', ' hours')
        if unit == 'd':
            delay = delay.replace('d', ' days')

        message = self.bot.trans.plugins.reminders.strings.added % (m.sender.first_name, delay, text)

        return self.bot.send_message(m, message, extra={'format': 'HTML'})


    def daemon(self):
        # print(self.reminders.list)
        while len(self.reminders.list) > 0 and self.reminders.list[0].alarm < time():
            m = Message(None, Conversation(self.reminders.list[0].chat_id), self.info, None)
            self.bot.send_message(m, self.reminders.list[0].text, extra={'format': 'HTML'})
            self.reminders.list.remove(self.reminders.list[0])
            self.reminders.store_database()


    @staticmethod
    def to_seconds(delaytime, unit):
        if unit == 's':
            return float(delaytime)
        elif unit == 'm':
            return float(delaytime) * 60
        elif unit == 'h':
            return float(delaytime) * 60 * 60
        elif unit == 'd':
            return float(delaytime) * 60 * 60 * 24


    def sort_reminders(self):
        if not 'list' in self.reminders:
            self.reminders.list = []

        if len(self.reminders.list) > 0:
            self.reminders.list = sorted(self.reminders.list, key=lambda k: k['alarm'])

        self.reminders.store_database()