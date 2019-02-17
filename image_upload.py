import logging
from urllib.request import urlretrieve
import config
from imgurpython import ImgurClient


imgur_client = ImgurClient(config.IMGUR_CLIENT_ID, config.IMGUR_CLIENT_SECRET)


def upload_image(file_name):
    try:
        return imgur_client.upload_from_path(file_name, anon=True)["link"]
    except Exception as e:
        logging.error("Uploading image error: " + str(e), exc_info=True)
