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

    # This response will only be used for the initial URL validation:
    if payload:
        return Response(payload['challenge']), 200
