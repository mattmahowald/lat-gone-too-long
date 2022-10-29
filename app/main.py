from flask import Flask, Response
from flask import request as flask_request

app = Flask(__name__)

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
        # An optional security measure - check to see if the
        # request is coming from an authorized Slack channel
        channel_id = payload['event']['channel']
        print(f"Message received in channel {channel_id}")

        message = None
        try:
            elements = [x for x in payload['event']['blocks']][0]['elements'][0]['elements']
            message = [e['text'].strip() for e in elements if e['type'] == 'text'][0]
            print(message)
        except Exception as e:
            print(e)
