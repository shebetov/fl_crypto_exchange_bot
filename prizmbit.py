import urllib.parse
import hashlib
import hmac
import requests
import time
import json
import logging
from chart_image import generate_chart
from image_upload import upload_image
from cachetools.func import ttl_cache
import websocket
import threading


logging.basicConfig(level=logging.DEBUG)


def cache_request(func):
    memo = {}
    ttl_config = {
        "MarketData/GetSymbols": 600,
        "MarketData/GetTicker": 3,
        "MarketData/GetOrderBook": 3,
        "Account/OpenOrders": 3,
        "Account/GetUserBalances": 3,
        "Account/GetCryptoAddress": 10,
        "Account/GetUserTransactions": 5,
        "Account/GetUserTrades": 3,
        "Transaction/GetUserAddressList": 10
    }

    def wrapper(self, method, path, **kwargs):
        ttl = ttl_config.get(path, None)
        if ttl is None:
            return func(self, method, path, **kwargs)
        key = (method, path,) + tuple(kwargs.values())
        cached_rv = memo.get(key, None)
        if (cached_rv is None) or (cached_rv[1] < time.time()):
            rv = func(self, method, path, **kwargs)
            memo[key] = (rv, time.time() + ttl)
            return rv
        else:
            return cached_rv[0]

    return wrapper


class PrizmBitAPI:

    BASE_URL = "https://api.prizmbit.com/api/po/"

    def __init__(self, c_id, c_secret):
        self.c_id = c_id
        self.c_secret = c_secret.encode('utf8')

    @cache_request
    def _request(self, method, path, **params):
        params = urllib.parse.urlencode(params)
        r = getattr(requests, method)(
            self.BASE_URL + path,
            params=params,
            headers={
                "X-ClientId": self.c_id,
                "X-Signature": hmac.new(self.c_secret, params.encode('utf8'), hashlib.sha256).hexdigest()
            }
        )
        print(path + " -> " + str(r._content))
        if r.status_code != 200: return None
        try:
            return r.json()
        except Exception as e:
            logging.error(e, exc_info=True)
            return {"error": "No response from API"}

    def get(self, path, **params):
        return self._request("get", path, **params)

    def post(self, path, **params):
        return self._request("post", path, **params)

    @ttl_cache(ttl=5)
    def load_24hchart_image(self, pair):
        t = int(time.time())
        d_chart = self.get("MarketData/GetChart", marketName=pair, to=t, period="5", **{"from": t-8640})
        if "error" in d_chart: return d_chart
        try:
            plt = generate_chart(pair, d_chart["t"], d_chart["o"], d_chart["h"], d_chart["l"], d_chart["c"], d_chart["v"])
            file_name = "files/chart24h_" + pair.replace("/", "-") + ".png"
            plt.savefig(file_name)
            return upload_image(file_name)
        except Exception as e:
            logging.error(e, exc_info=True)
            return {"error": "Error while generating image"}


class PrizmBitWebsocket:
    # Don't grow a table larger than this amount. Helps cap memory usage.
    MAX_TABLE_LEN = 200
    URL = "wss://wss.prizmbit.com/"
    _all_wss = []

    def __init__(self, init_data):
        """Connect to the websocket and initialize data stores."""
        #self.logger = logging.getLogger("prizmbit_webscoket")
        #_sh = logging.FileHandler("logs/ws_logs.txt")
        #_sh.setLevel(logging.DEBUG)
        #_sh.setFormatter(logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"))
        #self.logger.addHandler(_sh)
        logging.debug("Initializing WebSocket.")

        self.exited = False

        # We can subscribe right in the connection querystring, so let's build that.
        # Subscribe to all pertinent endpoints
        logging.info("Connecting...")
        self.__connect(init_data)
        logging.info("Got all market data. Starting.")

    def exit(self):
        """Call this to exit - will close websocket."""
        self.exited = True
        self.ws.close()

    def __connect(self, init_data):
        """Connect to the websocket in a thread."""
        logging.debug("Starting thread")

        self.ws = websocket.WebSocketApp(
            self.URL,
            on_message=self.__on_message,
            on_close=self.__on_close,
            on_open=self.__on_open,
            on_error=self.__on_error,
        )

        self.wst = threading.Thread(target=lambda: self.ws.run_forever())
        self.wst.daemon = True
        self.wst.start()
        self._all_wss.append((self.ws, self.wst))
        logging.debug("Started thread")

        # Wait for connect before continuing
        conn_timeout = 5
        while not self.ws.sock or not self.ws.sock.connected and conn_timeout:
            time.sleep(1)
            conn_timeout -= 1
        if not conn_timeout:
            logging.error("Couldn't connect to WS! Exiting.")
            self.exit()
            raise websocket.WebSocketTimeoutException(
                "Couldn't connect to WS! Exiting."
            )
        self.ws.send(init_data)

    def __on_message(self, message):
        """Handler for parsing WS messages."""
        logging.info(message)
        with open("ws_dump.txt", "a") as f:
            f.write(message + "\n")

    def __on_error(self, error):
        """Called on fatal websocket errors. We exit on these."""
        if not self.exited:
            logging.error("Error : %s" % error)
            raise websocket.WebSocketException(error)

    def __on_open(self):
        """Called when the WS opens."""
        logging.debug("Websocket Opened.")

    def __on_close(self):
        """Called on websocket close."""
        logging.info("Websocket Closed")

#ws = PrizmBitWebsocket("{marketId:1}")
#ws = PrizmBitWebsocket('{clientId:"ca494cadf96b4634aa9e4d8c777a3509f85628c7c3bc4fdf94d2c690c126d888"}')
#ws.wst.join()
