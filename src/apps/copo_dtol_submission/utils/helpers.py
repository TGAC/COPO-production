import os
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django_tools.middlewares import ThreadLocal
from common.lookup.dtol_lookups import API_KEY
from urllib.parse import urljoin
import requests
import json
from common.utils.logger import Logger
from common.utils import helpers

public_name_service = helpers.get_env('PUBLIC_NAME_SERVICE')

def query_public_name_service(sample_list):
    headers = {"api-key": API_KEY}
    url = urljoin(public_name_service, 'tol-ids')  # public-name
    Logger().log("name service urls: " + url)
    try:
        r = requests.post(url=url, json=sample_list, headers=headers, verify=False)
        if r.status_code == 200:
            resp = json.loads(r.content)
            print(resp)
        else:
            # in the case there is a network issue, just return an empty dict
            resp = {}
        Logger().log("name service response: " + str(resp))
        return resp
    except Exception as e:
        Logger.log("PUBLIC NAME SERVER ERROR: " + str(e))
        return {}

def get_group_membership_asString():
    r = ThreadLocal.get_current_request()
    gps = r.user.groups.all()
    gps = [str(g) for g in gps]
    return gps

def get_env(env_key):
    env_value = str()
    if env_key in os.environ:
        env_value = os.getenv(env_key)

    # resolve for file assignment
    file_env = os.environ.get(env_key + "_FILE", str())
    if len(file_env) > 0:
        try:
            with open(file_env, 'r') as mysecret:
                data = mysecret.read().replace('\n', '')
                env_value = data
        except:
            pass

    return env_value

def notify_frontend(action="message", msg=str(), data={}, html_id="", profile_id="", group_name='dtol_status'):
    """
        function notifies client changes in Sample creation status
        :param profile_id:
        :param action:
        :param msg:
        :return:
    """
    # type points to the object type which will be passed to the socket and is a method defined in consumer.py
    event = {"type": "msg", "action": action, "message": msg, "data": data, "html_id": html_id}
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        group_name,
        event
    )
    return True

 
