import os

from flask import Flask, request, render_template, redirect, url_for

from logging.config import dictConfig
import time
import json

import session_states
import constants
from token_manager import load_tokens, save_tokens, clear_tokens
from oauth_utils import generate_pkce_pair, start_authorization, exchange_code_for_token, get_xero_tenant_id, refresh_access_token
from data_manager import get_customers, get_items, create_invoice
from pdf_processor import build_invoice
from threading import Thread, Event, Lock

scan_thread = None
scan_thread_started = False
scan_thread_lock = Lock()
stop_scan_event = Event()

app = Flask(__name__)

# Configure logging
dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s | %(module)s >>> %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "default",
            }
        },
        "root": {"level": "INFO", "handlers": ["console"]},
    }
)

# Load tokens

if __name__ == "__main__":
    app.run("localhost", port=5000, debug=True)

@app.route("/auth")
def start_auth():
    app.logger.info("Loading tokens from file...")
    # Build your auth URL and redirect
    tokens = load_tokens()
    if tokens:
        app.logger.info("Tokens loaded from file")
        try:
            session_states.refresh_token = tokens["refresh_token"].strip()
            session_states.access_token = tokens["access_token"].strip()

            session_states.xero_tenant_id = get_xero_tenant_id(session_states.access_token)
            app.logger.info(f"Tokens valid.")
        except Exception as e:
            app.logger.error("Error loading tokens: %s", e)

            try:
                # attempt refresh token refresh
                app.logger.info(f"Refreshing access token. . .")
                refresh_tokens()
                return redirect(url_for("main_function"))
            except Exception as e1:

                # Most likely refresh token is invalid.
                app.logger.info(f"Error attempt to refresh token {e1}.")
                clear_tokens()
                return render_template("callback-error.html")

        return redirect(url_for("main_function"))

    if not tokens:
        app.logger.info("Tokens missing from file. Starting auth flow...")
        url = retrieve_tokens()
        return redirect(url)

def retrieve_tokens():
    session_states.code_verifier, session_states.code_challenge = generate_pkce_pair()

    # ==== BUILD AUTH URL ====
    url = start_authorization(
        session_states.CONST_AUTH_URL,
        session_states.CONST_CLIENT_ID,
        session_states.CONST_REDIRECT_URI,
        session_states.CONST_SCOPES,
        session_states.code_challenge
    )
    app.logger.info("Opening Web Browser to: %s", url)

    return url

def refresh_tokens():
    session_states.refresh_token, session_states.access_token = (
        refresh_access_token(session_states.refresh_token, session_states.CONST_CLIENT_ID))

    app.logger.info("Access token refreshed!")

    save_tokens({"tenant_id": session_states.xero_tenant_id, "refresh_token": session_states.refresh_token,
                 "access_token": session_states.access_token})
@app.route("/callback")
def callback():
    if request.args.get("error"):
        app.logger.error("Could not get auth code. Aborting application. . . %s")
        return render_template("callback-error.html")
    else:
        session_states.auth_code = request.args.get("code")
        app.logger.info("Auth code received. generating tokens...")

        session_states.refresh_token, session_states.access_token = exchange_code_for_token(
            session_states.CONST_CLIENT_ID,
            session_states.CONST_REDIRECT_URI,
            session_states.auth_code,
            session_states.code_verifier
        )
        app.logger.info("Tokens generated. Getting tenant ID...")

        session_states.xero_tenant_id = get_xero_tenant_id(session_states.access_token)
        # app.logger.info("Tenant ID: %s", session_states.xero_tenant_id)

        save_tokens({"tenant_id": session_states.xero_tenant_id, "refresh_token": session_states.refresh_token, "access_token": session_states.access_token})
        return redirect(url_for("main_function"))

def initialize_data():
    global scan_thread, scan_thread_started
    app.logger.info("Initializing data...")

    constants.inv_customers = get_customers(session_states.access_token, session_states.xero_tenant_id)
    constants.inv_items = get_items(session_states.access_token, session_states.xero_tenant_id)

    with scan_thread_lock:
        if not scan_thread_started:
            stop_scan_event.clear()
            app.logger.info("Starting PDF scanner thread...")
            scan_thread = Thread(target=scan_for_pdfs, daemon=True)
            scan_thread.start()
            scan_thread_started = True
        else:
            app.logger.info("PDF scanner thread already running.")

def scan_for_pdfs():
    WATCH_FOLDER = "/WatchPDFs"
    PROCESSED_FOLDER = os.path.join(WATCH_FOLDER, "processed")
    ERROR_FOLDER = os.path.join(WATCH_FOLDER, "error")

    os.makedirs(WATCH_FOLDER, exist_ok=True)
    os.makedirs(PROCESSED_FOLDER, exist_ok=True)
    os.makedirs(ERROR_FOLDER, exist_ok=True)

    app.logger.info("Waiting for files...")

    while not stop_scan_event.is_set():
        try:
            files = [f for f in os.listdir(WATCH_FOLDER) if f.lower().endswith('.pdf')]
            if files:
                start = time.time()
                for filename in files:
                    file_path = os.path.join(WATCH_FOLDER, filename)
                    processed_path = os.path.join(PROCESSED_FOLDER, filename)
                    error_path = os.path.join(ERROR_FOLDER, filename)

                    try:
                        # Create invoice body
                        invoice = build_invoice(file_path)

                        # Send invoice to Xero
                        # Uncomment and wrap this in error handling:
                        create_invoice(invoice, session_states.access_token, session_states.xero_tenant_id)

                        os.replace(file_path, processed_path)
                        app.logger.info(f"Processed file: {processed_path}")

                    except Exception as e:
                        error_str = str(e).lower()
                        try:
                            error_json = json.loads(str(e))
                            status = error_json.get("Status")
                        except Exception as ex:
                            app.logger.error(f"Unexpected error occurred: {ex}.")
                            status = None

                        # Stop scanner on fatal Xero auth error (401 Unauthorized)
                        if status == 401 or "401" in error_str or "unauthorized" in error_str or "tokenexpired" in error_str:
                            app.logger.error(
                                "401 Unauthorized or token expired. Attempting to refresh access token. . .")
                            try:
                                refresh_tokens()
                            except Exception as e1:
                                app.logger.error(
                                    f"Error on attempting refresh token {e1}")
                                app.logger.error(f"Error with file: {file_path}. {e}")
                                os.replace(file_path, error_path)
                                stop_scan_event.set()

                end = time.time()
                app.logger.info(f"Time elapsed processing {len(files)} files is {end - start:.4f} seconds")

        except Exception as e:
            app.logger.error(f"[Watcher] Unexpected error: {e}")

        time.sleep(10)
@app.route("/")
def main_function():
    try:
        initialize_data()
        return render_template("main-page.html")
    except Exception as e:
        app.logger.error(f"Error initializing data. Authentication required. . .{e}")
        return start_auth()