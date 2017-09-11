import base64
import httplib2
import oauth2client
import os
import smtplib

from apiclient import errors, discovery

from email.mime.text import MIMEText

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
# from flask_restful import fields
from flask_restful import Api
from flask_restful import Resource
from flask_restful import reqparse

from oauth2client import client, tools

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


class SendMailAbstract(object):
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
        pass


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
        mail_class = self._get_class_by_email(app.config['MAIL_FROM'])
        mail = mail_class(addresses, message, mime_type, subject)
        print('CLASS: {}'.format(mail.__class__))
        if mail.send_mail():
            return 'OK', 200
        else:
            return 'Fail', 400

    def _get_class_by_email(self, email):
        if 'redhat.com' in email:
            return SendMailApi
        return SendMail


class SendMailApi(SendMailAbstract):
    def __init__(self, addresses, message, mime_type, subject):
        super(SendMailApi, self).__init__(addresses, message, mime_type,
                                          subject)

        self.credentials = self.get_credentials()

    def get_credentials(self):
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir,
                                       'gmail-python-email-send.json')
        store = oauth2client.file.Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(
                    os.path.join(
                        credential_dir, app.config['CLIENT_SECRET_FILE']),
                    app.config['SCOPES'])
            flow.user_agent = app.config['APPLICATION_NAME']
            credentials = tools.run_flow(flow, store)
        return credentials

    # def send_mail(self, sender, to, subject, msg_html, msg_plain):
    def send_mail(self):
        http = self.credentials.authorize(httplib2.Http())
        service = discovery.build('gmail', 'v1', http=http)
        message = self.create_message_html()
        result = self.send_message_internal(service, "me", message)
        return result

    def send_message_internal(self, service, user_id, message):
        try:
            message = (service.users().messages().send(
                userId=user_id, body=message).execute())
            print 'Message Id: %s' % message['id']
            return message
        except errors.HttpError, error:
            print 'An error occurred: %s' % error
            return "Error"
        return "OK"

    def create_message_html(self):
        msg = MIMEText(self.message, self.mime_type)
        msg['Subject'] = self.subject
        msg['From'] = self.mail_from
        msg['To'] = ",".join(self.addresses)
        return {'raw': base64.urlsafe_b64encode(msg.as_string())}


class SendMail(SendMailAbstract):
    def __init__(self, addresses, message, mime_type, subject):
        super(SendMail, self).__init__(addresses, message,
                                       mime_type, subject)

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

if __name__ == '__main__':
    sendmail = SendMailApi(['arxcruz@gmail.com'], 'test', 'html', 'test email api')
