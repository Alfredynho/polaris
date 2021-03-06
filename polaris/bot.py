from polaris.types import AutosaveDict, Message
from polaris.utils import set_logger, is_int
from multiprocessing import Process, Queue
from threading import Thread
from time import sleep
import importlib, logging, time, re, traceback, sys, os


class Bot(object):
    def __init__(self, name):
        self.name = name
        self.config = AutosaveDict('bots/%s.json' % self.name)
        self.trans = AutosaveDict('polaris/translations/%s.json' % self.config.translation)
        self.bindings = importlib.import_module('polaris.bindings.%s' % self.config.bindings).bindings(self)
        self.inbox = Queue()
        self.outbox = Queue()
        self.started = False
        self.plugins = None
        self.info = None


    def sender_worker(self):
        try:
            logging.debug('Starting sender worker...')
            while self.started:
                msg = self.outbox.get()
                logging.info(' %s@%s sent [%s] %s' % (msg.sender.first_name, msg.conversation.title, msg.type, msg.content))
                self.bindings.send_message(msg)
        except KeyboardInterrupt:
            pass


    def messages_handler(self):
        try:
            logging.debug('Starting message handler...')
            while self.started:
                msg = self.inbox.get()
                try:
                    logging.info(
                        '%s@%s sent [%s] %s' % (msg.sender.first_name, msg.conversation.title, msg.type, msg.content))
                except AttributeError:
                    logging.info(
                        '%s@%s sent [%s] %s' % (msg.sender.title, msg.conversation.title, msg.type, msg.content))

                # p = Process(target=self.on_message_receive, args=(msg,), name='%s' % self.name)
                # p.daemon = True
                # p.start()
                self.on_message_receive(msg)

        except KeyboardInterrupt:
            pass


    def start(self):
        self.started = True
        self.plugins = self.init_plugins()
        self.info = self.bindings.get_me()

        logging.info('Connected as %s (@%s)' % (self.info.first_name, self.info.username))

        jobs = []
        jobs.append(Process(target=self.bindings.receiver_worker, name='%s R.' % self.name))
        jobs.append(Process(target=self.sender_worker, name='%s S.' % self.name))
        jobs.append(Process(target=self.cron_jobs, name='%s' % self.name))

        for job in jobs:
            job.daemon = True
            job.start()

        Process(target=self.messages_handler, name='%s' % self.name).start()


    def stop(self):
        self.started = False


    def init_plugins(self):
        plugins = []

        logging.info('Importing plugins...')

        for plugin in self.config.plugins:
            try:
                plugins.append(importlib.import_module('polaris.plugins.' + plugin).plugin(self))
                logging.info('  [OK] %s ' % (plugin))
            except Exception as e:
                logging.error('  [Failed] %s - %s ' % (plugin, str(e)))

        logging.info('  Loaded: ' + str(len(plugins)) + '/' + str(len(self.config.plugins)))

        return plugins


    def on_message_receive(self, msg):
        try:
            triggered = False

            for plugin in self.plugins:
                # Always do this action for every message. #
                if hasattr(plugin, 'always'):
                    plugin.always(msg)

                # Check if any command of a plugin matches. #
                for command in plugin.commands:
                    if 'command' in command:
                        if self.check_trigger(command['command'], msg, plugin):
                            break

                    if 'friendly' in command:
                        if self.check_trigger(command['friendly'], msg, plugin):
                            break

                    if 'shortcut' in command:
                        if len(command['shortcut']) < 3:
                            shortcut = command['shortcut'] + ' '
                        else:
                            shortcut = command['shortcut']

                        if self.check_trigger(shortcut, msg, plugin):
                            break

        except Exception as e:
            logging.exception(e)


    def check_trigger(self, command, message, plugin):
        # If the commands are not /start or /help, set the correct command start symbol. #
        if command == '/start' or command == '/help':
            trigger = command.replace('/', '^/')

        elif message.type == 'inline_query':
            trigger = trigger.replace(self.config.prefix, '')

        else:
            trigger = command.replace('/', '^' + self.config.prefix)

        if message.content and re.compile(trigger).search(message.content.lower()):
                if hasattr(plugin, 'inline') and message.type == 'inline_query':
                    plugin.inline(message)
                else:
                    plugin.run(message)

                return True


    def cron_jobs(self):
        while(self.started):
            for plugin in self.plugins:
                if hasattr(plugin, 'cron'):
                    plugin.cron()

            sleep(5)


    # METHODS TO MANAGE MESSAGES #
    def send_message(self, msg, content, type='text', reply=None, extra=None):
        message = Message(None, msg.conversation, self.info, content, type, reply=reply, extra=extra)
        self.outbox.put(message)


    def forward_message(self, msg, id):
        self.outbox.put(Message(None, msg.conversation, self.info, msg.content, 'forward',
                                extra={"message": msg.id, "conversation": id}))

    def answer_inline_query(self, msg, results, offset=None):
        self.outbox.put(Message(None, msg.conversation, self.info, results, 'inline_results', extra={"offset": offset}))


    # THESE METHODS DO DIRECT ACTIONS #
    def get_file(self, file_id, only_url=False):
        try:
            return self.bindings.get_file(file_id, only_url)
        except:
            return None


    def invite_user(self, msg, user):
        try:
            self.bindings.invite_chat_member(msg.conversation.id, user)
        except PermissionError:
            return None
        except Exception:
            return False
        else:
            return True


    def kick_user(self, msg, user):
        try:
            self.bindings.kick_chat_member(msg.conversation.id, user)
        except PermissionError:
            return None
        except Exception:
            return False
        else:
            return True


    def unban_user(self, msg, user):
        try:
            self.bindings.unban_chat_member(msg.conversation.id, user)
        except PermissionError:
            return None
        except Exception:
            return False
        else:
            return True


    def chat_info(self, chat):
        try:
            return self.connector.chat_info(chat)
        except:
            return chat


    def send_alert(self, text):
        pass
