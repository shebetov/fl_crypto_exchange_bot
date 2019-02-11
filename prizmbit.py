import urllib.parse
import hashlib
import hmac
import requests


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
