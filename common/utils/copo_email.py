import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings


class CopoEmail:

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

