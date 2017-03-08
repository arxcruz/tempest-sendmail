import smtplib

from email.mime.text import MIMEText

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
# from flask_restful import fields
from flask_restful import Api
from flask_restful import Resource
from flask_restful import reqparse

__version__ = '0.1'

app = Flask(__name__)
app.config.from_object('websiteconfig')
app.secret_key = '3fb99a0f-eb39-4f58-89da-e68303f7b14f'

limiter = Limiter(app, key_func=get_remote_address)

api = Api(app)

request_parser = reqparse.RequestParser()
request_parser.add_argument('addresses', action='append')
request_parser.add_argument('message')
request_parser.add_argument('mime_type')
request_parser.add_argument('subject')


class SendMailResource(Resource):
    # @marshal_with(request_fields)
    decorators = [limiter.limit('10/hour')]

    def post(self):
        args = request_parser.parse_args()
        addresses = args['addresses']
        print('ADDRESSES: {}'.format(addresses))
        message = args['message']
        mime_type = args['mime_type']
        subject = args['subject']
        mail = SendMail(addresses, message, mime_type, subject)
        if mail.send_mail():
            return 'OK', 200
        else:
            return 'Fail', 400


class SendMail(object):
    def __init__(self, addresses, message, mime_type, subject):
        self._addresses = addresses
        self._message = message
        self._mime_type = mime_type
        self._subject = subject
        self.mail_from = app.config['MAIL_FROM']

    @property
    def addresses(self):
        return self._addresses

    @property
    def message(self):
        return self._message

    @property
    def mime_type(self):
        return self._mime_type

    @property
    def subject(self):
        return self._subject

    def send_mail(self):

        msg = MIMEText(self.message, self.mime_type)
        msg['Subject'] = self.subject
        msg['From'] = self.mail_from
        msg['To'] = ",".join(self.addresses)

        s = smtplib.SMTP(app.config['SMTP_SERVER'])
        s.ehlo()
        s.starttls()
        s.login(app.config['USERNAME'], app.config['PASSWORD'])

        try:
            s.sendmail(self.mail_from, self.addresses, msg.as_string())
            s.quit()
        except Exception:
            return False

        return True

api.add_resource(SendMailResource, '/api/v1.0/sendmail', endpoint='sendmail')
