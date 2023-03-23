#Created by fshaw at 04/06/2020
from django_tools.middlewares import ThreadLocal

def get_group_membership_asString():
    r = ThreadLocal.get_current_request()
    gps = r.user.groups.all()
    gps = [str(g) for g in gps]
    return gps
