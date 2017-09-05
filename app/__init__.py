# coding=utf-8

from flask import Flask
from flask_compress import Compress
from flask_caching import Cache
import logging

FORMAT = "%(asctime)-15s %(levelname)s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
Compress(app)

from app import views
