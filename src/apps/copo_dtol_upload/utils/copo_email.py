import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings
from src.apps.copo_core.models import User
from common.utils.copo_email import CopoEmail


class Email:

    def __init__(self):
        self.messages = {
            "new_manifest" : "<h4>Manifest Available</h4><p>A manifest has been uploaded for approval. Please follow the link to proceed</p><h5>{} - {}</h5><p><a href='{}'>{}</a></p>",
        }

    def notify_manifest_pending_approval(self, data, **kwargs):
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
        if len(users) > 0:
            for u in users:
                email_addresses.append(u.email)

            demo_notification = ""
            is_new = "New "
            if "demo" in data:
                demo_notification = "DEMO SERVER NOTIFICATION: "
            if not kwargs.get("is_new", True) :            
                is_new = "Modified "
            msg = self.messages["new_manifest"].format(kwargs["title"], demo_notification + kwargs["description"], data, data)
            sub = demo_notification + is_new + kwargs["project"] + " Manifest - " + kwargs["title"]
            CopoEmail().send(to=email_addresses, sub=sub, content=msg, html=True)
