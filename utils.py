import sys
import logging
from copy import deepcopy
from datetime import datetime
import dateparser
from threading import Thread


def chunks(data, n):
    for i in range(0, len(data), n):
        yield data[i:i + n]


def intersection(lst1, lst2):
    for v in lst1:
        if v in lst2:
            yield v


def replace_markdown(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def threaded(daemon=False):
    def threaded_dec(func):
        def threaded_func(*args, **kwargs):
            thread = Thread(target=func, args=args, kwargs=kwargs, daemon=daemon)
            thread.start()
            return thread
        return threaded_func
    return threaded_dec


def parse_date_period(text):
    d1_raw, d2_raw = text.split("-")
    d1_raw, d2_raw = d1_raw.strip(" "), d2_raw.strip(" ")
    d1 = d2 = None
    if len(d1_raw) != 0:
        d1 = dateparser.parse(d1_raw, languages=['ru', 'en'], settings={'PREFER_DATES_FROM': 'past'})
    if len(d2_raw) != 0:
        d2 = dateparser.parse(d2_raw, languages=['ru', 'en'], settings={'PREFER_DATES_FROM': 'past'})
    return d1, d2

def setup_logger(logger, level, filename):
    formatter = logging.Formatter('%(levelname)-8s[%(asctime)s: (%(pathname)-100s)%(filename)-20s:%(lineno)-4d] %(message)s')
    formatter_console = logging.Formatter('%(levelname)-8s[%(asctime)s %(filename)-20s:%(lineno)-4d] %(message)s')
    fh = logging.FileHandler(filename, 'a', 'utf-8')
    fh.setLevel(level)
    fh.setFormatter(formatter)
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(level)
    sh.setFormatter(formatter_console)
    #logging.basicConfig(format=formatter, level=level, handlers=[fh, sh])
    logger.setLevel(level)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger



def _r_hash_list(l):
    for i in range(len(l)):
        if isinstance(l[i], dict):
            l[i] = _r_hash_dict(l[i])
        elif isinstance(l[i], list):
            l[i] = _r_hash_list(l[i])
    return tuple(l)


def _r_hash_dict(d):
    for k, v in d.items():
        if isinstance(v, dict):
            d[k] = _r_hash_dict(v)
        elif isinstance(v, list):
            d[k] = _r_hash_list(v)
    return tuple(sorted(d.items()))


def to_hashable_dict(d):
    return _r_hash_dict(deepcopy(d))
