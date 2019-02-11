#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, django
from fl_crypto_exchange_bot import settings
sys.path.append(settings.BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fl_crypto_exchange_bot.settings")
django.setup()

import logging
import time
import datetime
import requests
import config
from text_data import TEXT
import utils
import telebot
from my_tg_api import UltraTeleBot
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from django.core.exceptions import ObjectDoesNotExist
from tgbot.models import *
from prizmbit import PrizmBitAPI



logging.basicConfig(format='%(levelname)-8s[%(asctime)s: (%(pathname)s)%(filename)-20s:%(lineno)-4d] %(message)s', level=(logging.DEBUG if config.DEBUG else logging.INFO), handlers=[logging.FileHandler(config.LOGS_FILE, 'a', 'utf-8')])  # , logging.StreamHandler(sys.stdout)])
sentry_sdk.init(dsn=config.SENTRY_API_URL, integrations=[LoggingIntegration()])

bot = UltraTeleBot(config.BOT_TOKEN)
client = PrizmBitAPI(config.CLIENT_ID, config.CLIENT_SECRET)


def get_user(user_id):
    try:
        return User.objects.get(user_id=user_id)
    except ObjectDoesNotExist:
        return None


def log_message(sender, user_id, message=None, intent=None):
    try:
        message = None if message is None else message.replace("\n", "\\n")
        with open(config.CHAT_LOGS_DIR + str(user_id) + ".txt", "a", encoding="utf-8") as f:
            if sender == "user":
                f.write("[" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "] user:  " + "{:<20}".format(str(intent)) + (str(message) if message else "") + "\n")
            elif sender == "agent":
                f.write("[" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "] agent:                     " + str(message) + "\n")
    except:
        logging.error("Log Message", exc_info=True)


# Telegram Funcs And Handlers


@bot.callback_query_handler(func=lambda call: True)
def callback_inline_handler(call):
    user = get_user(call.from_user.id)


@bot.message_handler(commands=['start'])
def reply_start(message):
    print(message.text)
    user = get_user(message.from_user.id)
    reply_markup = bot.create_keyboard([[TEXT["m"]["b1"]], [TEXT["m"]["b2"]], [TEXT["m"]["b3"]]], one_time=False)
    tg_user_name = (message.from_user.first_name + ((" " + str(message.from_user.last_name)) if getattr(message.from_user, "last_name", None) else ""))


@bot.message_handler(content_types=['text'])
def text_handler(message):
    print(message.text)
    user = get_user(message.from_user.id)


# request handling

def handle_requests(environ, start_response):
    try:
        start_response('200 OK', [('Content-Type', 'application/json')])
        update = telebot.types.Update.de_json(environ["wsgi.input"].read().decode("utf-8"))
        logging.info("TG UPDATE " + str(update))
        bot.process_new_updates([update])
        return "!".encode()
    except Exception as e:
        logging.critical("Exception in webhook on_post func: " + str(e), exc_info=True)
        try:
            bot.tg_api(bot.send_message, config.TG_ADMIN_ID, "Cant handle update, because of error: " + str(e))
        except:
            pass


if __name__ == "__main__":
    if config.POLLING:
        bot.remove_webhook()
        bot.polling(none_stop=True)
    else:
        bot.set_webhook(url="".join(config.HOST))
        import bjoern, shutil, os
        try:
            os.remove(config.SOCKET_PATH)
        except:
            pass
        bjoern.listen(handle_requests, "unix:" + config.SOCKET_PATH)
        shutil.chown(config.SOCKET_PATH, 'username', 'usergroup')
        os.chmod(config.SOCKET_PATH, 0o770)
        bjoern.run()
