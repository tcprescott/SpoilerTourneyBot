import gspread
from datetime import datetime
from pytz import timezone
from oauth2client.service_account import ServiceAccountCredentials

tz = timezone('EST')

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

credentials = ServiceAccountCredentials.from_json_keyfile_name('cfg/spoilertourneybot_googlecreds.json', scope)
gc = gspread.authorize(credentials)

# Open a worksheet from spreadsheet with one shot
wks = gc.open_by_key("1udRdY3sX23HVMR_MckeDGGCFhMw-Rm1MINOO6IK5S4g").sheet1

wks.append_row(
   [
      str(datetime.now(tz)),
      'Synack#1337',
      '1',
      'BEEF'
   ]
)