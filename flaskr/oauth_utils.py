import os, base64, hashlib, requests
from datetime import time
from urllib.parse import urlencode


def generate_pkce_pair():
    verifier = base64.urlsafe_b64encode(os.urandom(40)).rstrip(b'=').decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b'=').decode()
    return verifier, challenge

def exchange_code_for_token(client_id, redirect_uri, code, verifier):
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": verifier
    }
    response = requests.post(
        "https://identity.xero.com/connect/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    response.raise_for_status()
    return response.json()["refresh_token"], response.json()["access_token"]

def refresh_access_token(refresh_token, client_id):
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token
    }
    response = requests.post(
        "https://identity.xero.com/connect/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    response.raise_for_status()
    return response.json()["refresh_token"], response.json()["access_token"]

def start_authorization(auth_url, client_id, redirect_uri, scopes, code_challenge):
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scopes,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }

    return f"{auth_url}?{urlencode(params)}"

def get_xero_tenant_id(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    response = requests.get("https://api.xero.com/connections", headers=headers)
    response.raise_for_status()
    return response.json()[0]["tenantId"]
