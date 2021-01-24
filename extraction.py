from __future__ import print_function

from googleapiclient.discovery import build

from settings import SPREADSHEET_ID, RANGE_NAME


def extract_from_google_sheets(creds):
    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                range=RANGE_NAME).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
    else:
        return values
