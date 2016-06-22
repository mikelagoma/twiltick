'''
Configuration Settings
'''

''' Uncomment to configure using the file.  
WARNING: Be careful not to post your account credentials on GitHub.

TWILIO_ACCOUNT_SID = "ACxxxxxxxxxxxxx" 
TWILIO_AUTH_TOKEN = "yyyyyyyyyyyyyyyy"
TWILIO_CALLER_ID = "+17778889999"
'''

import os
account_sid = os.environ.get('TWILIO_ACCOUNT_SID', None)
auth_token = os.environ.get('TWILIO_AUTH_TOKEN', None)
