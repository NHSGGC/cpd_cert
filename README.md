# cpd_cert
To install, activate virtualenv and `pip install -r requirements.txt`. Create a new `settings.py` from the template `settings_sample.py`, then run `./main.py`.

1. Extracts data from Google Sheets linked to a Google Form,
1. inputs the data into a PDF certificate,
1. sends PDF as attachment to email address of form submitter.

Will run on a loop with a 2 minute interval until interrupted.

### Settings
**SPREADSHEET_ID** parameter in `settings.py` should be obtained from  
[https://docs.google.com/spreadsheets/d/**SPREADSHEET_ID**/edit](https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit)

### Cache
Any email address that is successfully sent a PDF will be added to `cache.pickle`. Be sure to delete this when running a new job.

### Auth
Authentication seems to fail in Microsoft Edge browser, so try Firefox or Google Chrome instead.

Note that if it has been a long time since last run, you might need to delete `token.pickle` to allow Google to
reauthenticate (should pop open in browser). Remember to authenticate using account **secretary.wosbspd@gmail.com**.

