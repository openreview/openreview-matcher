# from .solver import *
# from . import metadata
# from . import utils


from flask import Flask


# app = Flask(__name__)
# per Flask doc, we hardcode the application package here.
app = Flask('matcher')

from matcher import routes