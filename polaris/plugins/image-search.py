from polaris.utils import get_input, send_request, download
from random import randint


class plugin(object):
    # Loads the text strings from the bots language #
    def __init__(self, bot):
        self.bot = bot
        self.commands = self.bot.trans.plugins.image_search.commands
        self.description = self.bot.trans.plugins.image_search.description

    # Plugin action #
    def run(self, m):
        input = get_input(m, ignore_reply=False)
        if not input:
            return self.bot.send_message(m, self.bot.trans.errors.missing_parameter, extra={'format': 'HTML'})

        url = 'https://www.googleapis.com/customsearch/v1'
        params = {
            'q': input,
            'searchType': 'image',
            'imgSize': 'xlarge',
            'alt': 'json',
            'num': 8,
            'start': 1,
            'key': self.bot.config.api_keys.google_developer_console,
            'cx': self.bot.config.api_keys.google_custom_search_engine
        }

        data = send_request(url, params)

        if not data:
            return self.bot.send_message(m, self.bot.trans.errors.connection_error)

        if data.searchInformation.totalResults == 0:
            return self.bot.send_message(m, self.bot.trans.errors.no_results)

        try:
            i = randint(0, len(data['items']))
            photo = data['items'][i]['link']
            caption = data['items'][i]['title']

        except Exception as e:
            logging.exception(e)
            photo = None

        if photo:
            return self.bot.send_message(m, photo, 'photo', extra={'caption': caption})
        else:
            return self.bot.send_message(m, self.bot.trans.errors.download_failed)
