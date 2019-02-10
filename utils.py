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
