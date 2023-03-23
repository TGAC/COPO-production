import os
from common.utils.logger import Logger

# print('COPO CWD is: ' + BASE_DIR + '\n')
# set the log level to the lowest level of logging you want to see
# i.e. for only errors, set to Loglvl.ERROR, for errors and warnings, Loglvl.WARNING, and for all, Loglvl.INFO
# logs sent through with Loglvl.ERROR will cause the execution of the current request to halt
LOGGER = Logger()

def skip_static_requests(record):
    if record.args[0].startswith('GET /static/'):  # filter whatever you want
        return False
    return True
# this code make django dev server skip all requests to /static/ dir making output easier to read
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        # use Django's built in CallbackFilter to point to your filter
        'skip_static_requests': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': skip_static_requests
        }
    },
    'formatters': {
        # django's default formatter
        'django.server': {
            '()': 'django.utils.log.ServerFormatter',
            #'format': '[%(server_time)s] %(message)s',
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s',
        }
    },
    'handlers': {
        # django's default handler...
        'django.server': {
            'level': 'INFO',
            'filters': ['skip_static_requests'],  # <- ...with one change
            'class': 'logging.StreamHandler',
            'formatter': 'django.server',
        },
    },
    'loggers': {
        # django's default logger
        'django.server': {
            'handlers': ['django.server'],
            'level': 'INFO',
            'propagate': False,
        },
    }
}
