import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings
from src.apps.copo_core.models import User


class CopoEmail:

    def __init__(self):
        self.messages = {
            "new_manifest":
                "<h4>New Manifest Available</h4>" +
                "<p>A new manifest has been uploaded for approval. Please follow the link to proceed</p>" +
                "<h5>{} - {}</h5>" +
                "<p><a href='{}'>{}</a></p>"
        }


    def send(self, to, sub, content, html=False):
        msg = MIMEMultipart()
        msg['From'] = settings.MAIL_ADDRESS

        msg['Subject'] = sub
        if html:
            msg.attach(MIMEText(content, 'html'))
        else:
            msg.attach(MIMEText(content, "plain"))
        self.mailserver = smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_SERVER_PORT)
        # identify ourselves to smtp gmail client
        self.mailserver.ehlo()
        # secure our email with tls encryption
        self.mailserver.starttls()
        # re-identify ourselves as an encrypted connection
        self.mailserver.ehlo()
        self.mailserver.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
        self.mailserver.sendmail(settings.MAIL_ADDRESS, to, msg.as_string())
        self.mailserver.quit()

    def notify_new_manifest(self, data, **kwargs):
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
            if "demo" in data:
                # if this is running on the demo server, add note into subject and content of email
                msg = self.messages["new_manifest"].format(kwargs["title"],
                                                           "DEMO SERVER NOTIFICATION - " + kwargs["description"], data,
                                                           data)
                sub = "DEMO SERVER NOTIFICATION: New " + kwargs["project"] + "Manifest - " + kwargs["title"]
            else:
                msg = self.messages["new_manifest"].format(kwargs["title"], kwargs["description"], data, data)
                sub = "New " + kwargs["project"] + " Manifest - " + kwargs["title"]
            self.send(to=email_addresses, sub=sub, content=msg, html=True)
