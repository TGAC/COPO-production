import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from common.dal.copo_da import Profile
from django.conf import settings
from src.apps.copo_core.models import SequencingCenter
from common.utils.copo_email import CopoEmail


class Email:

    def __init__(self):
        self.messages = {
            "sample_rejected" : "<h4>Following samples are rejected by ENA</h4><h5>{} - {}</h5><ul>{}</ul>"
        }


    def notify_sample_rejected_after_approval(self, **kwargs):
        # get email addresses of users in sequencing center
        users = []
        p_id = kwargs.get("profile_id", "")
        if p_id != "":
            profile = Profile().get_record(p_id)
            sequencing_centers = profile.get("sequencing_center", [])
            for sc in sequencing_centers:
                center = SequencingCenter.objects.get(name=sc)
                users += center.users.all()
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
