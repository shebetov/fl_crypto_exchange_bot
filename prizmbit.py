import urllib.parse
import hashlib
import hmac
import requests
import time
from chart_image import generate_chart


class PrizmBitAPI:

    BASE_URL = "https://api.prizmbit.com/api/po/"

    def __init__(self, c_id, c_secret):
        self.c_id = c_id
        self.c_secret = c_secret.encode('utf8')

    def _request(self, method, path, **params):
        params = urllib.parse.urlencode(params)
        r = getattr(requests, method)(
            self.BASE_URL + path + "?" + params,
            headers={
                "X-ClientId": self.c_id,
                "X-Signature": hmac.new(self.c_secret, params.encode('utf8'), hashlib.sha256).hexdigest()
            }
        )
        return r.json()

    def get(self, path, **params):
        return self._request("get", path, **params)

    def post(self, path, **params):
        return self._request("post", path, **params)

    def gen_24hchart_image(self, pair):
        t = int(time.time())
        d_chart = self.get("MarketData/GetChart", marketName=pair, to=t, period="5", **{"from": t-8640})
        plt = generate_chart(pair, d_chart["t"], d_chart["o"], d_chart["h"], d_chart["l"], d_chart["c"], d_chart["v"])
        plt.savefig("images/chart24h_" + pair.replace("/", "-") + ".png")
