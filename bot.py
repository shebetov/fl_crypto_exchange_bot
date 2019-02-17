#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, django
from fl_crypto_exchange_bot import settings
sys.path.append(settings.BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fl_crypto_exchange_bot.settings")
django.setup()

import logging
import time
from datetime import datetime
import decimal
import config
from text_data import TEXT
import utils
import math
import pandas
import dateparser
import telebot
from my_tg_api import UltraTeleBot, ApiException
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from django.core.exceptions import ObjectDoesNotExist
from tgbot.models import *
from prizmbit import PrizmBitAPI


logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(format='%(levelname)-8s[%(asctime)s: (%(pathname)s)%(filename)-20s:%(lineno)-4d] %(message)s', level=(logging.DEBUG if config.DEBUG else logging.INFO), handlers=[logging.FileHandler(config.LOGS_FILE, 'a', 'utf-8')])  # , logging.StreamHandler(sys.stdout)])
sentry_sdk.init(dsn=config.SENTRY_API_URL, integrations=[LoggingIntegration()])

bot = UltraTeleBot(config.BOT_TOKEN)
client = PrizmBitAPI(config.CLIENT_ID, config.CLIENT_SECRET)

TEMP_DATA = {}

D_TRANS = {
  "pages": 1,
  "transactionList": [
    {
      "id": 435,
      "ConfirmationId": "99e7caf70e474295989337282652a913",
      "userId": 352,
      "userName": "UserName",
      "currencyId": 15,
      "currencyTitle": "ETH",
      "transactionStatus": 1,
      "date": "2018-11-17T04:52:20+06:00",
      "amount": 0.001,
      "destination": None,
      "destinationTag": None,
      "destinationPublicKey": None,
      "cryptoTxId": None,
      "details": None,
      "transactionType": 1,
      "method": "Code"
    }
  ] * 20
}

D_TRADES = [
  {
    "tradeId": 6184521,
    "orderId": 26362733,
    "cliOrdId": None,
    "marketId": 14,
    "marketName": "ETH/USD",
    "side": 1,
    "amount": 1.5,
    "price": 176.02,
    "fee": 0.26403,
    "feeCurrency": "Dollar",
    "dateCreated": "2018-11-16T20:49:23+06:00"
  },
  {
    "tradeId": 6184522,
    "orderId": 26362736,
    "cliOrdId": None,
    "marketId": 12,
    "marketName": "ZEC/USD",
    "side": 1,
    "amount": 0.3,
    "price": 108.51,
    "fee": 0.032553,
    "feeCurrency": "Dollar",
    "dateCreated": "2018-11-16T21:41:54+06:00"
  }
] * 20

D_ADDR = {"addressList":[{"id":86,"currencyId":6,"currencyTitle":"PZM","isUsed":False,"address":"PRIZM-FSEE-U8TC-GHGW-5NWAE","publicKey":"91afa0e15489c478770ecae25ef09eb0a6c412219207b0216d2731d03acb4965","tagMessage":None,"label":None,"amount":0.0,"transactionsCount":0,"dateCreated":"2019-02-16 06:50:13Z"},{"id":84,"currencyId":5,"currencyTitle":"BTC","isUsed":False,"address":"36NMuvS65zhrbp1vHMNuU8dGsbiWFw3pxV","publicKey":None,"tagMessage":None,"label":None,"amount":0.0,"transactionsCount":0,"dateCreated":"2019-02-11 19:20:18Z"}],"pages":1}

D_ORD = [
  {
    "id": 26362735,
    "cliOrdId": None,
    "accountId": 104,
    "marketId": 14,
    "marketName": "ETH/USD",
    "side": 0,
    "orderQty": 1.2,
    "leavesQty": 1.2,
    "price": 174.3,
    "stopPrice": 0,
    "limitPrice": 0,
    "orderStatus": 0,
    "orderType": 0,
    "cancelDate": None,
    "dateCreated": "2018-11-16T20:49:48+06:00"
  },
  {
    "id": 26362734,
    "cliOrdId": None,
    "accountId": 104,
    "marketId": 14,
    "marketName": "ETH/USD",
    "side": 0,
    "orderQty": 1.5,
    "leavesQty": 1.5,
    "price": 177.86,
    "stopPrice": 0,
    "limitPrice": 0,
    "orderStatus": 0,
    "orderType": 0,
    "cancelDate": None,
    "dateCreated": "2018-11-16T20:49:43+06:00"
  }
]

"""

CHAT STATUS
m - main
t_sp{pair} - pair view
t_sp_co - create order
t_sp_co1 - enter Amount
t_sp_co2 - enter Price
t_sp_co3 - enter StopPrice
t_sp_co4 - enter LimitPrice 
t_sp_mo - view my orders by pair

"""


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
                f.write("[" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "] user:  " + "{:<20}".format(str(intent)) + (str(message) if message else "") + "\n")
            elif sender == "agent":
                f.write("[" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "] agent:                     " + str(message) + "\n")
    except:
        logging.error("Log Message", exc_info=True)


def gen_csv(data, fieldnames):
    with open('import.csv', mode='w') as csv_file:
        writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(fieldnames)
        for row in data:
            writer.writerow([row[field] for field in fieldnames])


# Telegram Funcs And Handlers


def try_redeem_code(user, text):
    d_redeem_code = client.post("Account/RedeemCode", Code=text)
    if "CodeId" in d_redeem_code:
        bot.tg_api(bot.send_message, user.user_id, "Код получен")
        return True
    else:
        return False


def send_exchange(user):
    kb_t = []
    kb_d = []
    all_pairs = [x["code"] for x in client.get("MarketData/GetSymbols")]
    for row in utils.chunks(all_pairs, 3):
        kb_t.append([])
        kb_d.append([])
        for x in row:
            kb_t[-1].append(x)
            kb_d[-1].append("t_sp" + x)
    bot.tg_api(bot.send_message, user.user_id, TEXT["t"], reply_markup=bot.create_keyboard(kb_t, kb_d), parse_mode="HTML")


def get_list_msg(user, data):
    text = data["title_ne"] if data["pages_count"] == 0 else data["title"]
    kb_t = []
    kb_d = []
    if data["pages_count"] > 0:
        list_index = 10 * data["current_page"]
        if data["type"] == "transaction":
            page = [TEXT["w_th_row"] % (i+1+list_index, x["transactionStatus"], x["currencyTitle"], x["amount"], x["date"]) for i, x in enumerate(data["raw"][list_index:list_index+10])]
        elif data["type"] == "trade":
            page = [TEXT["t_sp_mt_row"] % (i+1+list_index, TEXT[{0: "t_sp_mt_buy", 1: "t_sp_mt_sell"}[x["side"]]], x["amount"], x["price"], x["dateCreated"]) for i, x in enumerate(data["raw"][list_index:list_index+10])]
        elif data["type"] == "address":
            page = [TEXT["list_address_row"] % (i+1, x["currencyTitle"], x["address"], x["publicKey"]) for i, x in enumerate(data["raw"][list_index:list_index+10])]
        text += "\n\n" + "\n".join([row for row in page])
        if data["pages_count"] > 1:
            text += "\n\nСтраница: %i/%i" % (data["current_page"]+1, data["pages_count"])
            kb_t.append(["<<", ">>"])
            kb_d.append(["list<"+data["id"], "list>"+data["id"]])
        kb_t.append(["CSV", "Excel"])
        kb_d.append(["listC" + data["id"], "listE"+data["id"]])
    kb_t.append(["Назад"])
    kb_d.append(["listB"+data["id"]])
    return text, bot.create_keyboard(kb_t, kb_d)


def get_t_sp_msg(pair):
    d_ticker = client.get("MarketData/GetTicker", marketName=pair)
    d_orderbook = client.get("MarketData/GetOrderBook", market=pair, limit=4)
    return (TEXT["t_sp"] % (
        pair, d_ticker["price"], d_ticker["low"], d_ticker["high"], d_ticker["volume"], d_ticker["price"],
        "\n".join(["%s     %s" % (x["price"], x["quantity"]) for x in d_orderbook["asks"]]),
        "\n".join(["%s     %s" % (x["price"], x["quantity"]) for x in d_orderbook["bids"]])
    )), bot.create_keyboard([[TEXT["t_sp_b1"]]], [["t_sp_b1" + pair]])


def get_t_sp_mo(user, pair):
    d_my_orders = client.post("Account/OpenOrders", All=False, Market=pair, Limit=99999, Offset=0)
    d_my_orders = D_ORD
    if len(d_my_orders) == 0:
        return TEXT["t_sp_mo1"] % pair, None
    else:
        text = TEXT["t_sp_mo"] % pair + "\n"
        for i, order in enumerate(d_my_orders):
            text += "\n" + TEXT["t_sp_mo_row"] % (
            order["id"], TEXT[{0: "t_sp_mo_buy", 1: "t_sp_mo_sell"}[order["side"]]], order["orderType"], order["leavesQty"])
            if order["price"]:
                text += " " + TEXT["t_sp_mo_1"] + ": " + str(order["price"])
            if order["stopPrice"]:
                text += " " + TEXT["t_sp_mo_2"] + ": " + str(order["stopPrice"])
            if order["limitPrice"]:
                text += " " + TEXT["t_sp_mo_3"] + ": " + str(order["limitPrice"])
        return text, bot.create_keyboard([[TEXT["t_sp_mo_b1"]]], [["t_sp_mo_b1" + pair]])


def get_t_co_msg(data):
    t_buy = TEXT["t_sp_co_b1"]
    t_sell = TEXT["t_sp_co_b2"]
    if data["OrderSide"] == "Buy":
        t_buy = "*" + t_buy + "*"
    elif data["OrderSide"] == "Sell":
        t_sell = "*" + t_sell + "*"
    keyboard = bot.create_keyboard(
        [[t_buy, t_sell], [TEXT["t_sp_co_b3"] % data["OrderType"]], [TEXT["t_sp_co_b4"] % data["AccountType"]],
         [TEXT["t_sp_co_b6"], TEXT["t_sp_co_b5"]]],
        [["t_sp_co_b1", "t_sp_co_b2"], ["t_sp_co_b3"], ["t_sp_co_b4"], ["t_sp_co_b6", "t_sp_co_b5"]]
    )
    return TEXT["t_sp_co"], keyboard


def get_t_co_next_status(data):
    if data["Amount"] is None:
        return "1"
    elif (data.get("Price", None) is None) and (data["OrderType"] == "FillOrKill"):
        return "2"
    elif (data.get("StopPrice", None) is None) and (data["OrderType"] == "StopLimit"):
        return "3"
    elif (data.get("LimitPrice", None) is None) and (data["OrderType"] in ("Limit", "StopLimit")):
        return "4"
    return "5"


def get_w_b1(user):
    d_accounts = client.post("Account/GetUserBalances", data="sss")
    kb_t = []
    kb_d = []
    is_one_account = len(d_accounts["userAccountList"]) == 1
    balances = []
    for account in d_accounts["userAccountList"]:
        for balance in account["balanceList"]:
            balances.append((account["accountType"], balance))
    for row in utils.chunks(balances, 3):
        kb_t.append([x[1]["currencyTitle"] + ("" if is_one_account else " (%s)"%x[0]) for x in row])
        kb_d.append(["w_b1_"+str(x[1]["id"]) for x in row])
    return "Выберите валюту для пополнения", bot.create_keyboard(kb_t, kb_d)


def send_wallet(user):
    d_balances = client.post("Account/GetUserBalances", data="sss")
    s = ""
    for account in d_balances["userAccountList"]:
        s += "\nАккаунт: " + str(account["accountType"])
        for balance in account["balanceList"]:
            s += "\n %s %s" % (balance["currencyTitle"], balance["availableBalance"])
    text = TEXT["w"] % s
    keyboard = bot.create_keyboard([[TEXT["w_b1"], TEXT["w_b2"]], [TEXT["w_b3"]], [TEXT["w_b4"]]])
    bot.tg_api(bot.send_message, user.user_id, text, reply_markup=keyboard, parse_mode="HTML")


@bot.message_handler(func=lambda message: True, content_types=['photo'])
def handle_photo(message):
    user = get_user(message.from_user.id)
    if user.status == "s_b3":
        data = TEMP_DATA[user.user_id]
        if "params" in data:
            file_upload_text = (("f1", "Add Proof of Address Photo"), ("f2", "Add Selfie"), ("f3", None))
            for field, text in file_upload_text:
                if field not in data["params"]:
                    data["params"][field] = 'https://api.telegram.org/file/bot%s/%s' %(config.BOT_TOKEN, bot.get_file(message.photo[-1].file_id).file_path)
                    if text is not None:
                        bot.tg_api(bot.send_message, message.chat.id, text)
                    break
            if file_upload_text[-1][0] in data["params"]:
                bot.tg_api(bot.send_message, message.chat.id, "Данные верификации отправлены на проверку")
                user.status = "m"
                user.save()
                del TEMP_DATA[user.user_id]
                reply_start(message)
                print(data["params"])
                # client.post("https://front.prizmbit.com/api/fo/Login/UploadUserFiles", )  # Content-Type: multipart/form-data; Authorization: 13bf29729b1496796efb2f998c27b2c9096297966d27c755118993278a025419
                """
                Form Data

                ------WebKitFormBoundaryhWWN88glWYlGjOFF
                Content-Disposition: form-data; name="files"; filename="id.png"
                Content-Type: image/png


                ------WebKitFormBoundaryhWWN88glWYlGjOFF
                Content-Disposition: form-data; name="files"; filename="address.png"
                Content-Type: image/png


                ------WebKitFormBoundaryhWWN88glWYlGjOFF
                Content-Disposition: form-data; name="files"; filename="selfie.png"
                Content-Type: image/png


                ------WebKitFormBoundaryhWWN88glWYlGjOFF--
                """
                # client.post("https://front.prizmbit.com/api/fo/Login/UserVerification", **{"firstName":"d","middleName":"vbn","lastName":"nv","birthday":"2000-01-01","citizenship":"vbn","country":"Russia","city":"Moscow","address":"fsgs","postalCode":"112233","passportNumber":"1","passportIssuedDate":"2018-01-01","passportExperationDate":"2048-01-01"})  # Authorization: 13bf29729b1496796efb2f998c27b2c9096297966d27c755118993278a025419


@bot.callback_query_handler(func=lambda call: True)
def callback_inline_handler(call):
    user = get_user(call.from_user.id)
    if call.data[:4] == "t_sp":
        if call.data[4:7] == "_b1":
            pair = call.data[7:]
            text, keyboard = get_t_sp_msg(pair)
            try:
                bot.tg_api(bot.edit_message_text, text, call.message.chat.id, call.message.message_id, reply_markup=keyboard, ignore_exc=True, drop_exc=True)
            except ApiException:
                bot.tg_api(bot.answer_callback_query, call.id, TEXT["t_sp_b1_answer"])
        elif call.data[4:9] == "_co_b":
            btn = call.data[9:]
            if btn == "1":
                TEMP_DATA[user.user_id]["OrderSide"] = "Buy"
            elif btn == "2":
                TEMP_DATA[user.user_id]["OrderSide"] = "Sell"
            elif btn == "3":
                TEMP_DATA[user.user_id]["OrderType"] = config.ORDER_TYPE_CHOICES[
                    (config.ORDER_TYPE_CHOICES.index(TEMP_DATA[user.user_id]["OrderType"]) + 1) % (
                                len(config.ORDER_TYPE_CHOICES))]
            elif btn == "4":
                TEMP_DATA[user.user_id]["AccountType"] = config.ACCOUNT_TYPE_CHOICES[
                    (config.ACCOUNT_TYPE_CHOICES.index(TEMP_DATA[user.user_id]["AccountType"]) + 1) % (
                                len(config.ACCOUNT_TYPE_CHOICES))]
            elif btn == "5":
                if TEMP_DATA[user.user_id]["OrderSide"] is None:
                    bot.tg_api(bot.answer_callback_query, call.id, TEXT["t_sp_co_e1"], show_alert=True)
                else:
                    bot.tg_api(bot.send_message, user.user_id, TEXT["t_sp_co1"])
                    user.status = "t_sp_co1"
                    user.save()
                return
            elif btn == "6":
                user.status = "m"
                del TEMP_DATA[user.user_id]
                reply_start(call)
                return
            text, keyboard = get_t_co_msg(TEMP_DATA[user.user_id])
            bot.tg_api(bot.edit_message_text, text, call.message.chat.id, call.message.message_id,
                       reply_markup=keyboard, ignore_exc=True)
        elif call.data[4:10] == "_mo_b1":
            pair = call.data[10:]
            bot.tg_api(bot.answer_callback_query, call.id, TEXT["t_sp_mo_b1_"])
            text, keyboard = get_t_sp_msg(pair)
            bot.tg_api(bot.send_message, call.message.chat.id, text, reply_markup=keyboard, parse_mode="HTML")
            bot.tg_api(bot.delete_message, call.message.chat.id, call.message.message_id)
            d_all_orders = client.post("Account/OpenOrders", All=False, Market=pair, Limit=99999, Offset=0)
            if len(d_all_orders) != 0:
                client.post("Trade/CancelOrders", command={"orderIdList": [x["id"] for x in d_all_orders]})
        else:
            pair = call.data[4:]
            keyboard = bot.create_keyboard([[TEXT["t_sp_b2"]], [TEXT["t_sp_b3"]], [TEXT["t_sp_b4"]], [TEXT["t_sp_b5"]]], one_time=False)
            bot.tg_api(bot.send_message, call.message.chat.id, TEXT["t_sp2"], reply_markup=keyboard)
            bot.tg_api(bot.delete_message, call.message.chat.id, call.message.message_id)
            user.status = "t_sp" + pair
            user.save()
            text, keyboard = get_t_sp_msg(pair)
            bot.tg_api(bot.send_message, call.message.chat.id, text, reply_markup=keyboard, parse_mode="HTML")
    elif call.data[0] == "w":
        if call.data[1:5] == "_b1_":
            d_address = client.post("Account/GetCryptoAddress", BalanceId=call.data[5:], GenerateNewAddress=False)
            bot.tg_api(bot.send_message, call.message.chat.id, "Адрес для пополнения:\n  " + str(d_address["address"]) + ("" if d_address["publicKey"] is None else ("\npublicKey:\n" + str(d_address["publicKey"]))))
        elif call.data[1:7] == "_b2_b1":
            bot.tg_api(bot.send_message, call.message.chat.id, "Введи адрес")
            TEMP_DATA[user.user_id] = {"_": "w_b2_b1", "Currency": call.data[7:], "Address": None, "Amount": None, "Details": None}
            user.status = "w_b2_b1"
            user.save()
        elif call.data[1:7] == "_b2_b2":
            bot.tg_api(bot.send_message, call.message.chat.id, "Введи кол-во")
            TEMP_DATA[user.user_id] = {"_": "w_b2_b2", "Currency": call.data[7:], "Amount": None, "Recipient": None, "Description": None}
            user.status = "w_b2_b2"
            user.save()
    elif call.data[0] == "s":
        if call.data[1:5] == "_b1_":
            #user.lang = call.data[5:]
            user.save()
            reply_start(call)
    elif call.data[:4] == "list":
        action = call.data[4]
        data = TEMP_DATA[user.user_id]
        if action == "<":
            data["current_page"] = (data["pages_count"] - 1) if data["current_page"] == 0 else (data["current_page"] - 1)
        elif action == ">":
            data["current_page"] = 0 if data["current_page"] == (data["pages_count"] - 1) else (data["current_page"] + 1)
        elif action == "B":
            del TEMP_DATA[user.user_id]
            if data["path"] == "w":
                user.status = "m"
                user.save()
                send_wallet(user)
            elif data["path"][0] == "t":
                pair = data["path"][1:]
                t, kb = get_t_sp_msg(pair)
                bot.tg_api(bot.send_message, call.message.chat.id, t, reply_markup=kb)
                user.status = "t_sp" + pair
                user.save()
            bot.tg_api(bot.delete_message, call.message.chat.id, call.message.message_id)
            return
        elif action == "C" or action == "E":
            columns = tuple()
            if data["type"] == "transaction":
                columns = ("date", "id", "ConfirmationId", "currencyTitle", "transactionStatus", "amount", "destination", "destinationPublicKey", "cryptoTxId", "transactionType", "method")
            elif data["type"] == "trade":
                columns = ("dateCreated", "tradeId", "orderId", "cliOrdId", "marketName", "side", "amount", "price", "fee", "feeCurrency")
            elif data["type"] == "address":
                columns = ("currencyTitle", "address", "publicKey", "label", "amount", "transactionsCount", "dateCreated")
            df = pandas.DataFrame(data["raw"], columns=columns)
            if action == "C":
                df.to_csv("files/import.csv")
                bot.tg_api(bot.send_document, user.user_id, open("files/import.csv", "rb"))
            else:
                df.to_excel('files/import.xlsx', sheet_name='sheet1', index=False)
                bot.tg_api(bot.send_document, user.user_id, open("files/import.xlsx", "rb"))
            return
        text, keyboard = get_list_msg(user, data)
        bot.tg_api(bot.edit_message_text, text, call.message.chat.id, call.message.message_id, reply_markup=keyboard, ignore_exc=True)


@bot.message_handler(commands=['start'])
def reply_start(message):
    user = get_user(message.from_user.id)
    if user is None:
        tg_user_name = (message.from_user.first_name + ((" " + str(message.from_user.last_name)) if getattr(message.from_user, "last_name", None) else ""))
        user = User.objects.create(user_id=message.from_user.id, name=message.from_user.first_name)
    reply_markup = bot.create_keyboard([[TEXT["m_b1"]], [TEXT["m_b2"]], [TEXT["m_b3"]]], one_time=False)
    bot.tg_api(bot.send_message, user.user_id, TEXT["m_n"], reply_markup=reply_markup, parse_mode="HTML")
    user.status = "m"
    user.save()
    TEMP_DATA.pop(user.user_id, False)


@bot.message_handler(content_types=['text'])
def text_handler(message):
    print(message.text)
    user = get_user(message.from_user.id)
    if user.status == "m":
        if message.text == TEXT["m_b1"]:
            send_exchange(user)
        elif message.text == TEXT["m_b2"]:
            send_wallet(user)
        elif message.text == TEXT["m_b3"]:
            bot.tg_api(bot.send_message, message.chat.id, "Настройки:", reply_markup=bot.create_keyboard([[TEXT["s_b1"]], [TEXT["s_b2"]], [TEXT["s_b3"]]]))
        elif message.text == TEXT["w_b4"]:
            bot.tg_api(
                bot.send_message,
                message.chat.id,
                TEXT["w_b4_"],
                reply_markup=bot.create_keyboard([[TEXT["w_b4_b1"]], [TEXT["w_b4_b2"]], [TEXT["w_b4_b3"]], [TEXT["w_b4_b4"]]])
            )
        elif message.text == TEXT["w_b1"]:
            text, keyboard = get_w_b1(user)
            bot.tg_api(bot.send_message, message.chat.id, text, reply_markup=keyboard)
        elif message.text == TEXT["w_b2"]:
            bot.tg_api(bot.send_message, message.chat.id, TEXT["w_b2_"], reply_markup=bot.create_keyboard([[TEXT["w_b2_b1"]], [TEXT["w_b2_b2"]]]))
        elif message.text == TEXT["w_b2_b1"]:
            d_accounts = client.post("Account/GetUserBalances", data="sss")
            currs = set()
            for account in d_accounts["userAccountList"]:
                for balance in account["balanceList"]:
                    currs.add(balance["currencyTitle"])
            kb_t = []
            kb_d = []
            for row in utils.chunks(list(currs), 3):
                kb_t.append([x for x in row])
                kb_d.append(["w_b2_b1"+x for x in row])
            bot.tg_api(bot.send_message, message.chat.id, TEXT["w_b2_b1_"], reply_markup=bot.create_keyboard(kb_t, kb_d))
        elif message.text == TEXT["w_b2_b2"]:
            d_accounts = client.post("Account/GetUserBalances", data="sss")
            currs = set()
            for account in d_accounts["userAccountList"]:
                for balance in account["balanceList"]:
                    currs.add(balance["currencyTitle"])
            kb_t = []
            kb_d = []
            for row in utils.chunks(list(currs), 3):
                kb_t.append([x for x in row])
                kb_d.append(["w_b2_b2"+x for x in row])
            bot.tg_api(bot.send_message, message.chat.id, TEXT["w_b2_b2_"], reply_markup=bot.create_keyboard(kb_t, kb_d))
        elif message.text == TEXT["w_b4_b1"]:
            data = dict(
                _="list",
                id=str(int(time.time())),
                path="w",
                type="transaction",
                current_page=0,
                api_path="Account/GetUserTransactions",
                api_params=dict(Offset=0, Limit=99999, SortDesc=False)
            )
            data["raw"] = client.post(data["api_path"], **data["api_params"])["transactionList"]
            data["raw"] = D_TRANS["transactionList"]
            data["pages_count"] = math.ceil(len(data["raw"])/10)
            data["title_ne"] = "Транзакций нет"
            data["title"] = "Транзакции:"
            TEMP_DATA[user.user_id] = data
            text, keyboard = get_list_msg(user, data)
            bot.tg_api(bot.send_message, message.chat.id, text, reply_markup=keyboard)
            user.status = "list" + data["id"]
            user.save()
        elif message.text == TEXT["w_b4_b2"]:
            data = dict(
                _="list",
                id=str(int(time.time())),
                path="w",
                type="trade",
                current_page=0,
                api_path="Account/GetUserTrades",
                api_params=dict(Offset=0, Limit=99999, SortDesc=False)
            )
            data["raw"] = client.post(data["api_path"], **data["api_params"])
            data["raw"] = D_TRADES
            data["pages_count"] = math.ceil(len(data["raw"])/10)
            data["title_ne"] = "Трейдов нет"
            data["title"] = "Трейды:"
            TEMP_DATA[user.user_id] = data
            text, keyboard = get_list_msg(user, data)
            bot.tg_api(bot.send_message, message.chat.id, text, reply_markup=keyboard)
            user.status = "list" + data["id"]
            user.save()
        elif message.text == TEXT["w_b4_b3"]:
            data = dict(
                _="list",
                id=str(int(time.time())),
                path="w",
                type="address",
                current_page=0,
                api_path="Account/GetUserTrades",
                api_params=dict(Offset=0, Limit=99999, SortDesc=False)
            )
            data["raw"] = client.post(data["api_path"], **data["api_params"])["addressList"]
            data["raw"] = D_ADDR["addressList"]
            data["pages_count"] = math.ceil(len(data["raw"])/10)
            data["title_ne"] = "Адресов нет"
            data["title"] = "Адреса:"
            TEMP_DATA[user.user_id] = data
            text, keyboard = get_list_msg(user, data)
            bot.tg_api(bot.send_message, message.chat.id, text, reply_markup=keyboard)
            user.status = "list" + data["id"]
            user.save()
        elif message.text == TEXT["w_b4_b4"]:
            return
            d_codes = client.post("Account/GetUserTrades", Offset=0, Limit=99999, SortDesc=False)
            d_codes = D_CODES
            data = dict(
                _="list",
                id=str(int(time.time())),
                path="w",
                type="code",
                raw=d_codes,
                current_page=0
            )
            data["pages_count"] = math.ceil(len(data["raw"])/10)
            data["title_ne"] = "Кодов нет"
            data["title"] = "Коды:"
            TEMP_DATA[user.user_id] = data
            text, keyboard = get_list_msg(user, data)
            bot.tg_api(bot.send_message, message.chat.id, text, reply_markup=keyboard)
            user.status = "list" + data["id"]
            user.save()
        elif message.text == TEXT["s_b1"]:
            kb_t, kb_d = [], []
            for k, v in config.LANGUAGES.items():
                kb_t.append([v])
                kb_d.append(["s_b1_"+k])
            bot.tg_api(bot.send_message, message.chat.id, "Выбери язык", reply_markup=bot.create_keyboard(kb_t, kb_d))
        elif message.text == TEXT["s_b2"]:
            pass
        elif message.text == TEXT["s_b3"]:
            bot.tg_api(bot.send_message, message.chat.id, TEXT["s_b3_"], parse_mode="HTML")
            TEMP_DATA[user.user_id] = {"_": "s_b3"}
            user.status = "s_b3"
            user.save()
        else:
            if not try_redeem_code(user, message.text):
                reply_start(message)
    elif user.status[:4] == "t_sp":
        if user.status[4:7] == "_co":
            try:
                decimal.Decimal(message.text)
            except decimal.InvalidOperation:
                bot.tg_api(bot.send_message, message.chat.id, TEXT["t_sp_co_e2"])
                return
            if user.status[7] == "1":
                TEMP_DATA[user.user_id]["Amount"] = message.text
            elif user.status[7] == "2":
                TEMP_DATA[user.user_id]["Price"] = message.text
            elif user.status[7] == "3":
                TEMP_DATA[user.user_id]["StopPrice"] = message.text
            elif user.status[7] == "4":
                TEMP_DATA[user.user_id]["LimitPrice"] = message.text
            next_step_id = get_t_co_next_status(TEMP_DATA[user.user_id])
            bot.tg_api(bot.send_message, message.chat.id, TEXT["t_sp_co"+next_step_id])
            if next_step_id == "5":
                del TEMP_DATA[user.user_id]["_"]
                client.post("Trade/TestOrder", **TEMP_DATA[user.user_id])
                del TEMP_DATA[user.user_id]
                reply_start(message)
            else:
                user.status = "t_sp_co" + next_step_id
                user.save()
        else:
            if user.status[4:7] == "_mo":
                pair = user.status[7:]
                if message.text.isdigit():
                    order_id = int(message.text)
                    d_orders = client.post("Account/OpenOrders", All=False, Market=pair, Limit=99999, Offset=0)
                    d_orders = D_ORD
                    if order_id in [x["id"] for x in d_orders]:
                        client.post("Trade/CancelOrder", OrderId=order_id)
                        bot.tg_api(bot.send_message, message.chat.id, "Ордер %i отменен." % order_id)
                    text, keyboard = get_t_sp_mo(user, pair)
                    bot.tg_api(bot.send_message, message.chat.id, text, reply_markup=keyboard)
                    return
            else:
                pair = user.status[4:]
            if message.text == TEXT["t_sp_b2"]:
                TEMP_DATA[user.user_id] = {"_": "t_sp_co", "Market": pair, "OrderSide": None, "OrderType": "Market",
                                           "AccountType": "Trade"}
                text, keyboard = get_t_co_msg(TEMP_DATA[user.user_id])
                bot.tg_api(bot.send_message, message.chat.id, text, reply_markup=keyboard)
            elif message.text == TEXT["t_sp_b3"]:
                text, keyboard = get_t_sp_mo(user, pair)
                bot.tg_api(bot.send_message, message.chat.id, text, reply_markup=keyboard)
                if keyboard is not None:  # not good
                    user.status = "t_sp_mo" + pair
                    user.save()
                    return
            elif message.text == TEXT["t_sp_b4"]:
                data = dict(
                    _="list",
                    id=str(int(time.time())),
                    path="t"+pair,
                    type="trade",
                    current_page=0,
                    api_path="Account/GetUserTrades",
                    api_params=dict(Market=pair, Offset=0, Limit=99999, SortDesc=False)
                )
                data["raw"] = client.post(data["api_path"], **data["api_params"])
                data["raw"] = D_TRADES
                data["pages_count"] = math.ceil(len(data["raw"])/10)
                data["title_ne"] = "Трейдов %s нет" % pair
                data["title"] = "Трейды %s:" % pair
                TEMP_DATA[user.user_id] = data
                text, keyboard = get_list_msg(user, data)
                bot.tg_api(bot.send_message, message.chat.id, text, reply_markup=keyboard)
                user.status = "list" + data["id"]
                user.save()
            elif message.text == TEXT["t_sp_b5"]:
                bot.tg_api(bot.send_photo, message.chat.id, client.load_24hchart_image(pair), TEXT["t_sp_graph"]%pair)
            else:
                if not try_redeem_code(user, message.text):
                    if user.status[4:7] == "_mo":
                        text, keyboard = get_t_sp_mo(user, pair)
                    else:
                        text, keyboard = get_t_sp_msg(pair)
                    bot.tg_api(bot.send_message, message.chat.id, text, reply_markup=keyboard)
                return
            user.status = "t_sp" + pair
            user.save()
    elif user.status == "w_b2_b1":
        if TEMP_DATA[user.user_id]["Address"] is None:
            bot.tg_api(bot.send_message, message.chat.id, "Введи кол-во")
            TEMP_DATA[user.user_id]["Address"] = message.text
        elif TEMP_DATA[user.user_id]["Amount"] is None:
            try:
                decimal.Decimal(message.text)
            except decimal.InvalidOperation:
                bot.tg_api(bot.send_message, message.chat.id, "Неправильный ввод")
                return
            bot.tg_api(bot.send_message, message.chat.id, "Введи описание перевода")
            TEMP_DATA[user.user_id]["Amount"] = message.text
        elif TEMP_DATA[user.user_id]["Details"] is None:
            TEMP_DATA[user.user_id]["Details"] = message.text
            del TEMP_DATA[user.user_id]["_"]
            d_withdraw = client.post("Account/CreateWithdrawal", **TEMP_DATA[user.user_id])
            if "error" in d_withdraw:
                bot.tg_api(bot.send_message, message.chat.id, "Ошибка. Проверь правильность введенных данных.")
            else:
                bot.tg_api(bot.send_message, message.chat.id, "Перевод создан. Статус: " + str(d_withdraw["transactionStatus"]))
            del TEMP_DATA[user.user_id]
            user.status = "m"
            user.save()
            reply_start(message)
    elif user.status == "w_b2_b2":
        if TEMP_DATA[user.user_id]["Amount"] is None:
            try:
                decimal.Decimal(message.text)
            except decimal.InvalidOperation:
                bot.tg_api(bot.send_message, message.chat.id, "Неправильный ввод")
                return
            bot.tg_api(bot.send_message, message.chat.id, "Введи никнейм получателя или 0, чтобы пропустить.")
            TEMP_DATA[user.user_id]["Amount"] = message.text
        elif TEMP_DATA[user.user_id]["Recipient"] is None:
            bot.tg_api(bot.send_message, message.chat.id, "Введи описание")
            TEMP_DATA[user.user_id]["Recipient"] = message.text
        elif TEMP_DATA[user.user_id]["Description"] is None:
            TEMP_DATA[user.user_id]["Description"] = message.text
            del TEMP_DATA[user.user_id]["_"]
            if TEMP_DATA[user.user_id]["Recipient"] == "0":
                del TEMP_DATA[user.user_id]["Recipient"]
            d_create_code = client.post("Account/CreateCode", **TEMP_DATA[user.user_id])
            if "error" in d_create_code:
                if d_create_code["error"] == "Insufficient funds":
                    bot.tg_api(bot.send_message, message.chat.id, "Недостаточно средств.")
                else:
                    bot.tg_api(bot.send_message, message.chat.id, "Ошибка. Проверь правильность введенных данных.")
            else:
                bot.tg_api(bot.send_message, message.chat.id, "Код создан: " + str(d_create_code["code"]))
            del TEMP_DATA[user.user_id]
            user.status = "m"
            user.save()
            reply_start(message)
    elif user.status == "s_b3":
        data = TEMP_DATA[user.user_id]
        if "params" in data:
            file_upload_text = (("f1", "Add ID photo"), ("f2", "Add Proof of Address Photo"), ("f3", "Add Selfie"))
            for field, text in file_upload_text:
                if field not in data["params"]:
                    bot.tg_api(bot.send_message, message.chat.id, text)
        else:
            rows = message.text.split("\n")
            if len(rows) == 12:
                fieldnames = (
                "firstName", "lastName", "middleName", "birthday", "citizenship", "country", "city", "address",
                "postalCode", "passportNumber", "passportExperationDate", "passportIssuedDate")
                params = {}
                for i, fieldname in enumerate(fieldnames):
                    if i in (3, 10, 11):
                        if rows[i].isdigit():
                            dt = None
                        else:
                            dt = dateparser.parse(rows[i], settings={'STRICT_PARSING': True})
                        if dt is None:
                            bot.tg_api(bot.send_message, message.chat.id, "Не удалось распознать формат даты: " + rows[i])
                            break
                        else:
                            params[fieldname] = dt.strftime("%Y-%m-%d")
                    else:
                        params[fieldname] = rows[i]
                else:
                    bot.tg_api(bot.send_message, message.chat.id, "Add ID photo")
                    TEMP_DATA[user.user_id] = {
                        "_": "s_b3",
                        "params": params
                    }
                    return
                bot.tg_api(bot.send_message, message.chat.id, TEXT["s_b3_"], parse_mode="HTML")
    elif user.status[:4] == "list":
        if TEMP_DATA.get(user.user_id, {}).get("id", None) == user.status[4:]:
            data = TEMP_DATA[user.user_id]
            if message.text.count("-") == 1:
                d1, d2 = utils.parse_date_period(message.text)
            else:
                d1 = d2 = None
            if d1 is None:
                if "From" in data["api_params"]:
                    del data["api_params"]["From"]
            else:
                data["api_params"]["From"] = d1.timestamp()
            if d2 is None:
                if "To" in data["api_params"]:
                    del data["api_params"]["To"]
            else:
                data["api_params"]["To"] = d2.timestamp()
            if data["type"] == "trade":
                data["raw"] = client.post(data["api_path"], **data["api_params"])
                data["raw"] = D_TRADES
            elif data["type"] == "transaction":
                data["raw"] = client.post(data["api_path"], **data["api_params"])["transactionList"]
                data["raw"] = D_TRANS["transactionList"]
            elif data["type"] == "address":
                data["raw"] = client.post(data["api_path"], **data["api_params"])["addressList"]
                data["raw"] = D_ADDR["addressList"]
            elif data["type"] == "code":
                pass
            data["pages_count"] = math.ceil(len(data["raw"]) / 10)
            if d1 is None and d2 is None:
                text = "Показаны все результаты"
            elif d1 is None:
                text = "Показаны результаты до %s. Введи \"-\" для отмены" % d2.strftime("%d.%m.%Y")
            elif d2 is None:
                text = "Показаны результаты с %s. Введи \"-\" для отмены" % d1.strftime("%d.%m.%Y")
            else:
                text = "Показаны результаты с %s по %s. Введи \"-\" для отмены" % (d1.strftime("%d.%m.%Y"), d2.strftime("%d.%m.%Y"))
            bot.tg_api(bot.send_message, message.from_user.id, text)
            text, keyboard = get_list_msg(user, TEMP_DATA[user.user_id])
            bot.tg_api(bot.send_message, message.from_user.id, text, reply_markup=keyboard)


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
        #bot.remove_webhook()
        while True:
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
