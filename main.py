import os
import pickle
from datetime import datetime
import time

from auth import authenticate_google_credentials
from extraction import extract_from_google_sheets, sheets_column_index
from transformation import modify_pdf
from distribution import send_email_pdf

from settings import OUTPUT_PDF_PATH, NAME_COL, GDC_NUM_COL, EMAIL_COL

if __name__ == "__main__":
    while True:
        creds = authenticate_google_credentials()
        rows = extract_from_google_sheets(creds)
        if rows:
            if os.path.exists('cache.pickle'):
                with open('cache.pickle', 'rb') as f:
                    cache = pickle.load(f)
            else:
                cache = {'emails': []}

            print(datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S"))
            for row in rows[1:]:
                name = row[sheets_column_index(NAME_COL)]
                gdc_num = str(row[sheets_column_index(GDC_NUM_COL)])
                email = row[sheets_column_index(EMAIL_COL)]

                if email not in cache['emails']:
                    print('Creating PDF for {} ({} - {})'.format(email, name, gdc_num))
                    modify_pdf(name, gdc_num)
                    msg = send_email_pdf(creds, destination=email)
                    if msg:
                        cache['emails'].append(email)
                        os.remove(OUTPUT_PDF_PATH)
                else:
                    print("Email already sent to {} ({} - {})".format(email, name, gdc_num))

            # Save the credentials for the next run
            with open('cache.pickle', 'wb') as f:
                pickle.dump(cache, f)

        time.sleep(120)
