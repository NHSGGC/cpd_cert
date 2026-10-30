from __future__ import print_function

import string

from googleapiclient.discovery import build

from settings import SPREADSHEET_ID, RANGE_NAME


def extract_from_google_sheets(creds, spreadsheet_id=SPREADSHEET_ID,
                               range_name=RANGE_NAME):
    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id,
                                range=range_name).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
    else:
        return values


def sheets_column_index(column: str):
    return sum(string.ascii_uppercase.index(c) + (idx * 26) for idx, c in enumerate(column))
