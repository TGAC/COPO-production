import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings
from src.apps.copo_core.models import User, SequencingCentre
from common.utils.copo_email import CopoEmail
from common.dal.copo_da import get_users_seq_centres, Profile


class Email:

    def __init__(self):
        self.messages = {
            "new_manifest" : "<h4>Manifest Available</h4><p>A manifest has been uploaded for approval. Please follow the link to proceed</p><h5>{} - {}</h5><p><a href='{}'>{}</a></p>",
        }

    def notify_manifest_pending_approval(self, data, **kwargs):
        
        # get email addresses of users in sequencing centre
        users = []
        p_id = kwargs.get("profile_id", "")
        if p_id != "":
            profile = Profile().get_record(p_id)
            sequencing_centres = profile.get("sequencing_centre", [])
            for sc in sequencing_centres:
                centre = SequencingCentre.objects.get(name=sc)
                users += centre.users.all()

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
