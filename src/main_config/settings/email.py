# settings for automatic email
from common.utils.helpers import get_env


MAIL_USERNAME = get_env('MAIL_USERNAME')
MAIL_PASSWORD = get_env('MAIL_PASSWORD')
MAIL_SERVER = get_env('MAIL_SERVER')
MAIL_SERVER_PORT = get_env('MAIL_PORT')
MAIL_ADDRESS = get_env('MAIL_ADDRESS')