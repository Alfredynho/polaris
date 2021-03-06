from polaris.types import json2obj
from html.parser import HTMLParser
from DictObject import DictObject
from polaris.types import AutosaveDict
from re import compile
import logging, requests, json, magic, mimetypes, tempfile, os, subprocess, re


def get_input(message, ignore_reply=True):
    if message.type == 'text' or message.type == 'inline_query':
        text = message.content
    else:
        return None

    if not ignore_reply and message.reply and message.reply.type == 'text':
        text += ' ' + message.reply.content

    if not ' ' in text:
        return None

    return text[text.find(" ") + 1:]


def get_command(message):
    if message.content.startswith(config.start):
        command = first_word(message.content).lstrip(config.start)
        return command.replace('@' + bot.username, '')
    elif message.type == 'inline_query':
        return first_word(message.content)
    else:
        return None


def is_command(self, number, text):
    if 'command' in self.commands[number - 1]:
        trigger = self.commands[number - 1]['command'].replace('/', self.bot.config.prefix).lower()
        if compile(trigger).search(text.lower()):
            return True

    if 'friendly' in self.commands[number - 1]:
        trigger = self.commands[number - 1]['friendly'].replace('/', self.bot.config.prefix).lower()
        if compile(trigger).search(text.lower()):
            return True

    if 'shortcut' in self.commands[number - 1]:
        trigger = self.commands[number - 1]['shortcut'].replace('/', self.bot.config.prefix).lower()
        if len(self.commands[number - 1]['shortcut']) < 3:
            trigger += ' '
        if compile(trigger).search(text.lower()):
            return True

    return False


def set_setting(bot, uid, key, value):
    settings = AutosaveDict('polaris/data/%s.settings.json' % bot.name)
    uid = str(uid)
    if not uid in settings:
        settings[uid] = {}
    settings[uid][key] = value
    settings.store_database()


def get_setting(bot, uid, key):
    settings = AutosaveDict('polaris/data/%s.settings.json' % bot.name)
    uid = str(uid)
    try:
        return settings[uid][key]
    except:
        return None


def del_setting(bot, uid, key):
    settings = AutosaveDict('polaris/data/%s.settings.json' % bot.name)
    uid = str(uid)
    del(settings[uid][key])
    settings.store_database()


def has_tag(bot, target, tag):
    tags = AutosaveDict('polaris/data/%s.tags.json' % bot.name)
    if target in tags and tag in tags[target]:
        return True
    else:
        return False


def set_tag(bot, target, tag):
    tags = AutosaveDict('polaris/data/%s.tags.json' % bot.name)
    if not target in tags:
        tags[target] = []

    if not tag in tags[target]:
        tags[target].append(tag)
        tags.store_database()


def del_tag(bot, target, tag):
    tags = AutosaveDict('polaris/data/%s.tags.json' % bot.name)
    tags[target].remove(tag)
    tags.store_database()


def is_admin(bot, uid):
    if bot.config.owner == uid:
        return True

    elif has_tag(bot, uid, 'admin') or has_tag(bot, uid, 'owner'):
        return True

    else:
        return False


def is_trusted(bot, uid):
    if is_admin(bot, uid) or has_tag(bot, uid, 'trusted'):
        return True

    else:
        return False


def is_mod(bot, uid, gid):
    if is_trusted(bot, uid) or has_tag(bot, uid, 'globalmod') or has_tag(bot, uid, 'mod:%s' % gid):
        return True

    else:
        return False


def first_word(text, i=1):
    try:
        return text.split()[i - 1]
    except:
        return False


def all_but_first_word(text):
    if ' ' not in text:
        return False
    return text.split(' ', 1)[1]


def last_word(text):
    if ' ' not in text:
        return False
    return text.split()[-1]


def is_int(number):
    try:
        number = int(number)
        return True
    except:
        return False


def send_request(url, params=None, headers=None, files=None, data=None, post=False, parse=True):
    try:
        if post:
            r = requests.post(url, params=params, headers=headers, files=files, data=data, timeout=100)
        else:
            r = requests.get(url, params=params, headers=headers, files=files, data=data, timeout=100)
    except:
        logging.error('Error making request to: %s' % r.url)
        print('Error making request to: %s' % r.url)
        return None

    if r.status_code != 200:
        logging.error(r.text)
        while r.status_code == 429:
            r = s.get(url, params=params, headers=headers, files=files, data=data)
    if parse:
        return DictObject(json.loads(r.text))
    else:
        return r.url


def get_coords(input):
    url = 'http://maps.googleapis.com/maps/api/geocode/json'
    params = {'address': input}

    data = send_request(url, params=params)

    if not data or data['status'] == 'ZERO_RESULTS':
        return False, False, False, False

    locality = data.results[0].address_components[0].long_name
    for address in data.results[0].address_components:
        if 'country' in address['types']:
            country = address['long_name']

    return (data['results'][0]['geometry']['location']['lat'],
            data['results'][0]['geometry']['location']['lng'],
            locality, country)


def download(url, params=None, headers=None, method='get'):
    try:
        if method == 'post':
            res = requests.post(url, params=params, headers=headers, stream=True)
        else:
            res = requests.get(url, params=params, headers=headers, stream=True)
        ext = os.path.splitext(url)[1].split('?')[0]
        f = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        for chunk in res.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
    except IOError as e:
        logging.error(e)
        return None
    f.seek(0)
    if not ext:
        f.name = fix_extension(f.name)
    # f.cose
    return f.name
    # return open(f.name, 'rb')


def save_to_file(res):
    ext = os.path.splitext(res.url)[1].split('?')[0]
    f = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    for chunk in res.iter_content(chunk_size=1024):
        if chunk:
            f.write(chunk)
    f.seek(0)
    if not ext:
        f.name = fix_extension(f.name)
    return open(f.name, 'rb')


def fix_extension(file_path):
    type = magic.from_file(file_path, mime=True)
    extension = str(mimetypes.guess_extension(type, strict=False))
    if extension is not None:
        # I hate to have to use this s***
        if extension.endswith('jpe'):
            extension = extension.replace('jpe', 'jpg')
        os.rename(file_path, file_path + extension)
        return file_path + extension
    else:
        return file_path


def get_short_url(long_url, api_key):
    url = 'https://www.googleapis.com/urlshortener/v1/url'
    params = {'longUrl': long_url, 'key': api_key}
    headers = {'content-type': 'application/json'}

    res = send_request(url, params=params, headers=headers, data=json.dumps(params), post=True)

    return res.id


def mp3_to_ogg(original):
    converted = tempfile.NamedTemporaryFile(delete=False, suffix='.ogg')
    conv = subprocess.Popen(
        ['avconv', '-i', original, '-ac', '1', '-c:a', 'opus', '-b:a', '16k', '-y', converted.name],
        stdout=subprocess.PIPE)

    while True:
        data = conv.stdout.read(1024 * 100)
        if not data:
            break
        converted.write(data)

    return converted.name


def remove_markdown(text):
    characters = ['_', '*', '[', '`', '(', '\\']
    aux = list()
    for x in range(len(text)):
        if x >= 0 and text[x] in characters and text[x - 1] != '\\':
            pass
        else:
            aux.append(text[x])
    return ''.join(aux)


def remove_html(text):
    text = re.sub('<[^<]+?>', '', text)
    text = text.replace('&lt;', '<');
    text = text.replace('&gt;', '>');
    return text
    s = HTMLParser()
    s.reset()
    s.reset()
    s.strict = False
    s.convert_charrefs = True
    s.fed = []
    s.feed(text)
    return ''.join(s.fed)


def set_logger(debug=False):
    logFormatterConsole = logging.Formatter("[%(processName)-11.11s]  %(message)s")
    logFormatterFile = logging.Formatter("%(asctime)s [%(processName)-11.11s] [%(levelname)-5.5s]  %(message)s")
    rootLogger = logging.getLogger()
    if debug:
        rootLogger.setLevel(logging.DEBUG)
    else:
        rootLogger.setLevel(logging.INFO)

    fileHandler = logging.FileHandler("bot.log", mode='w')
    fileHandler.setFormatter(logFormatterFile)
    rootLogger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatterConsole)
    rootLogger.addHandler(consoleHandler)

    logging.getLogger("requests").setLevel(logging.WARNING)
