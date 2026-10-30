#! /usr/bin/env python3
import os
import pickle
from datetime import datetime
import time

from auth import authenticate_google_credentials
from extraction import extract_from_google_sheets, sheets_column_index
from transformation import modify_pdf
from distribution import send_email_pdf

from settings import (
    EMAIL_BODY,
    EMAIL_COL,
    EMAIL_SUBJECT,
    GDC_NUM_COL,
    GDC_OFFSET_INCHES,
    INPUT_PDF_PATH,
    NAME_COL,
    NAME_OFFSET_INCHES,
    OUTPUT_PDF_PATH,
    RANGE_NAME,
    SPREADSHEET_ID,
)


def process_job(creds, job, dry_run=False, redirect_to=None, max_sends=None):
    """Process outstanding certificates for one explicitly configured job.

    A dry run creates each PDF but does not call Gmail or alter the sent cache.
    redirect_to is intended for a single end-to-end test and does not alter the
    sent cache either.
    """
    rows = extract_from_google_sheets(
        creds,
        spreadsheet_id=job['spreadsheet_id'],
        range_name=job['range_name'],
    )
    if not rows:
        return {'sent': 0, 'already_sent': 0, 'would_send': 0, 'recipients': []}

    cache_path = job['cache_path']
    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            cache = pickle.load(f)
    else:
        cache = {'emails': []}

    sent = already_sent = 0
    recipients = []
    for row in rows[1:]:
        name = row[sheets_column_index(job['name_col'])]
        gdc_num = str(row[sheets_column_index(job['gdc_num_col'])])
        email = row[sheets_column_index(job['email_col'])]
        if email in cache['emails']:
            already_sent += 1
            print("Email already sent to {} ({} - {})".format(email, name, gdc_num))
            continue

        if max_sends is not None and len(recipients) >= max_sends:
            break

        print('Creating PDF for {} ({} - {})'.format(email, name, gdc_num))
        modify_pdf(
            name,
            gdc_num,
            input_path=job['input_pdf_path'],
            output_path=job['output_pdf_path'],
            name_offset_inch=job['name_offset_inches'],
            gdc_offset_inch=job['gdc_offset_inches'],
        )
        recipients.append(email)
        if dry_run:
            os.remove(job['output_pdf_path'])
            continue

        destination = redirect_to or email
        subject = job['email_subject']
        if redirect_to:
            subject = '[TEST for {}] {}'.format(email, subject)
        msg = send_email_pdf(
            creds,
            destination=destination,
            path_to_pdf=job['output_pdf_path'],
            body=job['email_body'],
            subject=subject,
        )
        if msg:
            sent += 1
            if not redirect_to:
                cache['emails'].append(email)
            os.remove(job['output_pdf_path'])

    if not dry_run and not redirect_to:
        with open(cache_path, 'wb') as f:
            pickle.dump(cache, f)
    return {
        'sent': sent,
        'already_sent': already_sent,
        'would_send': len(recipients),
        'recipients': recipients,
    }


LEGACY_JOB = {
    'spreadsheet_id': SPREADSHEET_ID,
    'range_name': RANGE_NAME,
    'name_col': NAME_COL,
    'gdc_num_col': GDC_NUM_COL,
    'email_col': EMAIL_COL,
    'input_pdf_path': INPUT_PDF_PATH,
    'output_pdf_path': OUTPUT_PDF_PATH,
    'name_offset_inches': NAME_OFFSET_INCHES,
    'gdc_offset_inches': GDC_OFFSET_INCHES,
    'email_body': EMAIL_BODY,
    'email_subject': EMAIL_SUBJECT,
    'cache_path': 'cache.pickle',
}

if __name__ == "__main__":
    while True:
        creds = authenticate_google_credentials()
        print(datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S"))
        process_job(creds, LEGACY_JOB)
        time.sleep(120)
