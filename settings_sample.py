# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

"""
EXTRACTION
"""
# The ID and range of a sample spreadsheet.
SPREADSHEET_ID = 'XXXX'
RANGE_NAME = 'Sheet Name!A:Z'

NAME_COL = 'A'
GDC_NUM_COL = 'B'
EMAIL_COL = 'C'


"""
TRANSFORMATION
"""
INPUT_PDF_PATH = "input.pdf"
OUTPUT_PDF_PATH = "output.pdf"

NAME_OFFSET_INCHES = {'x': 0, 'y': 0}
GDC_OFFSET_INCHES = {'x': 0, 'y': 0}


"""
DISTRIBUTION
"""
EMAIL_BODY = """
This will appear in the body of the email.
"""

EMAIL_SUBJECT = "This will appear as email subject."
