# -*- coding: utf-8 -*-
from utils import *

def process(msg):
    if ((str(msg['chat']['id']) in groups and groups[str(msg['chat']['id'])]['special'] == 'admin') or
            (str(msg['chat']['id']) in groups and groups[str(msg['chat']['id'])]['special'] == 'alerts') or
            (str(msg['chat']['id']) in groups and groups[str(msg['chat']['id'])]['special'] == 'log')):
        log = False
    else:
        log = True

    if log:
        if msg['text'] != '':
            if msg['chat']['id'] != msg['from']['id'] and msg['chat']['type'] == 'private':
                msg['chat']['title'] = msg['chat']['first_name']

            message = escape_markup(msg['text'])
            message = message.replace(bot['first_name'] + ' ', '')
            message += line()

            if 'username' in msg['from']:
                message += '👤 @' + msg['from']['username'] + ' (' + str(msg['from']['id']) + ')\n'
            else:
                message += '👤 ' + str(msg['from']['id']) + '\n'

            if msg['chat']['type'] != 'private':
                message += '👥 ' + msg['chat']['title'] + ' (' + str(msg['chat']['id']) + ')\n'
            message += '✉ ' + str(msg['message_id'])

            for group in groups.items():
                if group[1]['special'] == 'log':
                    send_message(group[0], message, parse_mode="Markdown")
        else:
            for group in groups.items():
                if group[1]['special'] == 'log':
                    forward_message(group[0], msg['chat']['id'], msg['message_id'])
    else:
        if 'reply_to_message' in msg and msg['reply_to_message']['from']['id'] == bot['id']:
            message_id = last_word(msg['reply_to_message']['text'].split('\n')[-1])
            chat_id = last_word(msg['reply_to_message']['text'].split('\n')[-2]).replace('(', '').replace(')', '')

            if message_id and chat_id:
                send_message(chat_id, msg['text'], reply_to_message_id=message_id, parse_mode="Markdown")
