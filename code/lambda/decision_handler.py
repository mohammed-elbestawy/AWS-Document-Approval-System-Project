import json
import os
import boto3
from datetime import datetime

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

TABLE_NAME = os.environ["TABLE_NAME"]
TOPIC_ARN  = os.environ["TOPIC_ARN"]
table = dynamodb.Table(TABLE_NAME)

ALLOWED_ACTIONS = {"approve", "reject"}


def lambda_handler(event, context):
    try:
        params = event.get("queryStringParameters") or {}
        doc_id = params.get("doc_id")
        token  = params.get("token")
        action = params.get("action")

        if not doc_id or not token or action not in ALLOWED_ACTIONS:
            return _html_response(400, "Invalid or incomplete request.")

        item = table.get_item(Key={"doc_id": doc_id}).get("Item")
        if not item:
            return _html_response(404, "Document not found.")

        # The token check is what actually authorizes this request —
        # anyone without the exact token from the original email cannot
        # act on this document, even if they guess a valid doc_id.
        if item.get("decision_token") != token:
            return _html_response(403, "Invalid or expired approval link.")

        if item.get("status") != "PENDING":
            return _html_response(200, f"This document was already marked as {item['status']}.")

        new_status = "APPROVED" if action == "approve" else "REJECTED"

        table.update_item(
            Key={"doc_id": doc_id},
            UpdateExpression="SET #s = :s, decided_at = :d",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": new_status, ":d": datetime.utcnow().isoformat()},
        )

        # Let the submitter know the outcome
        sns.publish(
            TopicArn=TOPIC_ARN,
            Subject=f"Your document '{item['title']}' was {new_status.lower()}"[:100],
            Message=(
                f"Hi {item['submitter_name']},\n\n"
                f"Your submission '{item['title']}' has been {new_status.lower()}."
            ),
        )

        return _html_response(200, f"Document has been {new_status.lower()}. Thank you.")

    except Exception as e:
        print(f"ERROR: {e}")
        return _html_response(500, "Something went wrong. Please try again later.")


def _html_response(code, message):
    # Returns a simple HTML page since this is opened directly
    # in a browser from an email link, not called via JavaScript.
    html = f"""
    <html><body style="font-family:sans-serif;text-align:center;padding:60px;">
    <h2>{message}</h2>
    </body></html>
    """
    return {
        "statusCode": code,
        "headers": {"Content-Type": "text/html"},
        "body": html,
    }
