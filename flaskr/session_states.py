import os
from dotenv import load_dotenv

CONST_AUTH_URL = os.getenv("CONST_AUTH_URL")
CONST_REDIRECT_URI = os.getenv("CONST_REDIRECT_URI")
CONST_CLIENT_ID = os.getenv("CONST_CLIENT_ID")
CONST_SCOPES = os.getenv("openid profile email accounting.transactions accounting.contacts offline_access")

code_verifier = None
code_challenge = None
auth_code = None
refresh_token = None
access_token = None
xero_tenant_id = None