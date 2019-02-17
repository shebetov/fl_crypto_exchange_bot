import time
import logging
import telebot
from telebot.apihelper import ApiException
import utils


#telebot.logger.setLevel(logging.DEBUG)
logger = logging.getLogger('TeleBot')


class UltraTeleBot(telebot.TeleBot):

    @staticmethod
    def create_keyboard(texts, datas=None, one_time=True, row_width=3):
        if datas:
            keyboard = telebot.types.InlineKeyboardMarkup(row_width=row_width)
            for i in range(len(texts)):
                keyboard.add(*[telebot.types.InlineKeyboardButton(texts[i][j], callback_data=datas[i][j]) for j in
                               range(len(texts[i]))])
        else:
            keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=one_time, resize_keyboard=True)
            for text in texts:
                keyboard.row(*text)
        return keyboard

    def tg_api(self, api_func, *args, **kwargs):
        logger.debug("tg_api " + api_func.__name__ + "(" + str(args) + " " + str(kwargs) + ")")
        drop_exc = kwargs.pop("drop_exc", False)
        ignore_exc = kwargs.pop("ignore_exc", False)
        try:
            return api_func(*args, **kwargs)
        except ApiException as e:
            if ignore_exc:
                logger.info(
                    "tg_api exception\n\t\t\tParams: " + str(args) + " " + str(kwargs) + "\n\t\t\tException: " + str(e))
            else:
                logger.error(
                    "tg_api exception\n\t\t\tParams: " + str(args) + " " + str(kwargs) + "\n\t\t\tException: " + str(e),
                    exc_info=True)
            if drop_exc:
                raise

    def tg_api_tries(self, api_func, *args, **kwargs):
        tries_count = kwargs.pop("tries_count", 3)
        drop_exc = kwargs.pop("drop_exc", False)
        for i in range(tries_count):
            try:
                return self.tg_api(api_func, drop_exc=True, *args, **kwargs)
            except ApiException:
                if tries_count - 1 == i:
                    logger.critical("tg_api_tries exception")
                    if drop_exc:
                        raise
                    return
            time.sleep(1)

    @utils.threaded()
    def tg_delete_message(self, msg):
        self.tg_api_tries(self.delete_message, msg.chat.id, msg.message_id)

    @utils.threaded()
    def tg_delete_message_batch(self, msgs):
        for msg in msgs:
            self.tg_api_tries(self.delete_message, msg.chat.id, msg.message_id)
            time.sleep(0.3)

    tg_api_threaded = utils.threaded()(tg_api)
    tg_api_tries_threaded = utils.threaded()(tg_api_tries)
