__author__ = 'felix.shaw@tgac.ac.uk - 24/07/15'

import requests

from django.conf import settings

def get_uid():
    r = requests.get(settings['WEB_SERVICES']['COPO']['get_id'])
    #print(r.text)
    return r.text