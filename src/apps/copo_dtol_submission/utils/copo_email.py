import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings
from src.apps.copo_core.models import User
from common.utils.copo_email import CopoEmail


class Email:

    def __init__(self):
        self.messages = {
            "sample_rejected" : "<h4>Following samples are rejected by ENA</h4><h5>{} - {}</h5><ul>{}</ul>"
        }


    def notify_sample_rejected_after_approval(self, **kwargs):
        # get users in group
        if kwargs.get("project", "") in ["DTOL", "ASG"]:
            users = User.objects.filter(groups__name='dtol_sample_notifiers')
        elif kwargs.get("project", "") in ["ERGA"]:
            users = User.objects.filter(groups__name='erga_sample_notifiers')
        elif kwargs.get("project", "") in ["DTOL_ENV"]:
            users = User.objects.filter(groups__name='dtolenv_sample_notifiers')
        else:
            users = []
        email_addresses = list()
        sub = ""
        samples = kwargs["rejected_sample"] 
        sample_arr = [f"<li>{key} : {samples[key]}</li>" for key in samples.keys()]
        sample_str = ' '.join(sample_arr)

        if len(users) > 0:
            for u in users:
                email_addresses.append(u.email)
            
            msg = self.messages["sample_rejected"].format(kwargs.get("title"," ") , kwargs.get("description"," "), sample_str)
            sub = settings.ENVIRONMENT_TYPE + " " + kwargs.get("project"," ") + " Manifest - " + kwargs.get("title"," ")
            CopoEmail().send(to=email_addresses, sub=sub, content=msg, html=True)
