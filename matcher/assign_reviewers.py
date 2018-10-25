import logging
import logging.handlers
import datetime
import os

logger = logging.getLogger(__name__)

from matcher import app

print("IN ASSIGN_REVIEWERS with __name__ == " + __name__ )



def app_init():

    # first get config settings for all matcher apps regardless of environment
    app.config.from_pyfile('../config.cfg')
    # now override using settings for this environment
    app.config.from_pyfile('../instance/config.cfg')
    # adds to the app config the OpenReview-py Client class.
    module = __import__("openreview")
    class_ = getattr(module, "Client")
    app.config['or_client'] = class_
    fh = logging.handlers.RotatingFileHandler(filename=app.config['LOG_FILE'], mode='a', maxBytes=1*1000*1000, backupCount=20)
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    app.logger.setLevel(logging.DEBUG)
    # We always have a file for a log of errors.  In dev environment, also log to console
    if app.config['ENV'] == 'development':
        app.logger.addHandler(ch)
    app.logger.addHandler(fh)
    app.logger.debug("\n\n" + str(datetime.datetime.now()) + " Starting ASSIGN_REVIEWERS app")
    app.logger.debug("---------------------------------------------------------")

    # app.run()


# dont put this in a if __name__ == '__main__'

app_init()

