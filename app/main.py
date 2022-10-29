from flask import Flask, Response
from flask import request as flask_request

import re

from english_words import english_words_set

FIRST_NAME_LAST_INITIAL_PATTERN = re.compile(r"([A-Z][A-Za-z]* [A-Z]|[A-Z][A-Za-z]*)")


app = Flask(__name__)


def parse_names(s):
    matches = FIRST_NAME_LAST_INITIAL_PATTERN.search(s)
    return [m for m in matches if m.lower() not in english_words_set]


@app.route("/", methods=['GET'])
def hello():
    return Response("Gone too long"), 200


@app.route('/slack/verify', methods=['POST'])
def inbound():
    """
    Inbound POST from Slack to test token
    """
    # When Slack sends a POST to your app, it will send a JSON payload:
    payload = flask_request.get_json()

    if payload:
        message = None
        try:
            elements = [x for x in payload['event']['blocks']][0]['elements'][0]['elements']
            message = [e['text'].strip() for e in elements if e['type'] == 'text'][0]
            names = parse_names(message)
            print(names)
        except Exception as e:
            print(e)

        return Response(payload.get('challenge')), 200
