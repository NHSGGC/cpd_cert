from __future__ import print_function

import base64
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

from apiclient import errors
from googleapiclient.discovery import build

from settings import OUTPUT_PDF_PATH, EMAIL_BODY, EMAIL_SUBJECT


def send_email_pdf(creds, destination, path_to_pdf=OUTPUT_PDF_PATH, body=EMAIL_BODY, subject=EMAIL_SUBJECT):
    try:
        email = MIMEMultipart()
        email['To'] = destination
        email['Subject'] = subject
        body = MIMEText(body)
        email.attach(body)

        with open(path_to_pdf, "rb") as f:
            attach = MIMEApplication(f.read(), _subtype="pdf")

        attach.add_header('Content-Disposition', 'attachment', filename=path_to_pdf)
        attach.add_header('Content-Type', "application", name=path_to_pdf)

        # Encode file in ASCII characters to send by email
        encoders.encode_base64(attach)

        # Add attachment to message and convert message to string
        email.attach(attach)

        text = {'raw': base64.urlsafe_b64encode(email.as_bytes()).decode()}

        # Call the Gmail API
        service = build('gmail', 'v1', credentials=creds)
        message = (service.users().messages().send(userId="me", body=text)
                   .execute())
        print('Message Id: %s' % message['id'])
        return message

    except errors.HttpError as error:
        print('An error occurred: %s' % error)
