from datetime import datetime
import httplib2
import logging
import os
import re

from flask import Flask, Response
from flask import request as flask_request
from googleapiclient import discovery
from google.oauth2 import service_account

from english_words import english_words_set
import pytz

# Pattern to match either
#  1. A capitalized word followed by a space and a capitalized letter
#  2. A capitalized word
FIRST_NAME_LAST_INITIAL_PATTERN = re.compile(r"([A-Z][A-Za-z]* [A-Z]|[A-Z][A-Za-z]*)")

# Scopes needed to write to google sheets
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets"
]
# Spreadsheet ID (found in the GSheet's URL)
SPREADSHEET_ID = '15W-5K8IPKVT84DqYRMgUZe4ArPdbqDq10PU1u4kWME4'
SHEET_NAME = "raw"

# Flask app and logging configuration
app = Flask(__name__)
gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)


def get_pdt_string():
    # Offset of PT from UTC
    utc_time = datetime.now(tz=pytz.utc)
    pdt_time = utc_time.astimezone(pytz.timezone('US/Pacific'))
    return str(pdt_time)

def parse_names(s):
    """Receives a string `s` from a slack message and returns found names.

    This uses a regular expression heuristic based on the pattern defined in
    the global space (FIRST_NAME_LAST_INITIAL_PATTERN). After finding all of
    the potential names, this filters out all english words.

    Note: This is probably a poor heuristic. Potential failures:
     - False positives from (1) detecting two capitalized words in sequence
       (s = "False Positive" return ["False P"]) and (2) teacher names
     - False negatives from (1) uncapitalized student names and (2) student
       first names that are in the english words set.

    The benefit of this heuristic, though, is that it requires zero maintenance
    versus maintaining a list of student names.
    """
    matches = FIRST_NAME_LAST_INITIAL_PATTERN.findall(s)
    return [m for m in matches if m.lower() not in english_words_set]


def write_to_sheets(names, message):
    try:
        secret_file = os.path.join(os.getcwd(), 'google-credentials.json')
        credentials = service_account.Credentials.from_service_account_file(
            secret_file,
            scopes=SCOPES
        )
        service = discovery.build('sheets', 'v4', credentials=credentials)

        # Extract the length of the list of entries in the sheet
        resp = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A1:A600000"
        ).execute()
        n_entries = len(resp.get("values", []))

        # Based on the number of entries and names, build the range to write to
        start_row = n_entries + 1
        end_row = n_entries + len(names)
        range_name = f"{SHEET_NAME}!A{start_row}:C{end_row}"
        app.logger.info(f"Writing {len(names)} names to range {range_name}")

        values = [[name, message, get_pdt_string()] for name in names]
        data = {
            'values' : values 
        }
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            body=data,
            range=range_name,
            valueInputOption='USER_ENTERED'
        ).execute()
        app.logger.info(f"Successfully wrote {len(names)} names to google sheets")
    except OSError as e:
        app.logger.error(f"Failed to write to google sheets:\n{e}")


def parse_slack_message(payload):
    message = None
    app.logger.info("Received a slack message {payload}")
    try:
        elements = [x for x in payload['event']['blocks']][0]['elements'][0]['elements']
        message = [e['text'].strip() for e in elements if e['type'] == 'text'][0]
        names = parse_names(message)
        return names, message
    except Exception as e:
        app.logger.error(f"An error occurred in parsing the slack message:\n{e}")


@app.route("/", methods=['GET'])
def index():
    """Home page of the web server."""
    app.logger.info("Somebody visited our homepage :D")
    return Response("Gone too long"), 200


@app.route('/slack/verify', methods=['POST'])
def inbound():
    """Inbound POST from Slack

    The payload is a nested structure and hopefully won't change if Slack
    maintains the API.


    """
    # When Slack sends a POST to your app, it will send a JSON payload:
    payload = flask_request.get_json()
    if payload:
        names, message = parse_slack_message(payload)
        write_to_sheets(names, message)
    return Response(payload.get('challenge')), 200
