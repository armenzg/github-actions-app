import logging
import os
from flask import jsonify, request, Flask

from .workflow_events import process_data

from sentry_sdk import init, capture_exception

APP_DSN = os.environ("APP_DSN")
if APP_DSN:
    # This tracks errors and performance of the app itself rather than GH workflows
    init(APP_DSN, traces_sample_rate=1.0, environment="development")

LOGGING_LEVEL = os.environ.get("LOGGING_LEVEL", "INFO")
logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL)

app = Flask(__name__)


def handle_event(data, headers):
    if headers.get("X-GitHub-Event") != "workflow_job":
        # We return 200 to make webhook not turn red
        return {"reason": "Event not supported."}, 200

    if data["action"] != "completed":
        return ({"reason": "We cannot do anything with this workflow state."}, 200)

    process_data(data)
    return {"reason": "OK"}, 200


@app.route("/", methods=["POST"])
def main():
    payload = {"reason": "There was an error."}
    http_code = 500
    try:
        payload, http_code = handle_event(request.json, request.headers)
    except Exception as e:
        # Report app issue to Sentry
        capture_exception(e)
        logging.exception(e)

    return jsonify(payload), http_code
