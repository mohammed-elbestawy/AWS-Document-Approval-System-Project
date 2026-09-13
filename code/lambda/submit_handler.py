import json
import os
import re
import uuid
import base64
import boto3
from datetime import datetime

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

BUCKET_NAME = os.environ["BUCKET_NAME"]
TABLE_NAME  = os.environ["TABLE_NAME"]
TOPIC_ARN   = os.environ["TOPIC_ARN"]
APP_BASE_URL = os.environ["APP_BASE_URL"]  # the CloudFront URL, used to build decision links
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")

table = dynamodb.Table(TABLE_NAME)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def lambda_handler(event, context):
    try:
        body = event.get("body", "{}")
        if isinstance(body, str):
            body = json.loads(body)

        required = ["submitter_name", "submitter_email", "title", "file_name", "file_base64"]
        missing = [f for f in required if not body.get(f)]
        if missing:
            return _response(400, {"error": "Missing fields: " + ", ".join(missing)})

        if not EMAIL_RE.match(body["submitter_email"]):
            return _response(400, {"error": "Invalid email format"})

        doc_id = str(uuid.uuid4())
        decision_token = str(uuid.uuid4())  # unguessable token used in the approval links

        # Decode and store the file in S3
        file_bytes = base64.b64decode(body["file_base64"])
        s3_key = f"documents/{doc_id}-{body['file_name']}"
        s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=file_bytes)

        table.put_item(Item={
            "doc_id": doc_id,
            "title": body["title"],
            "submitter_name": body["submitter_name"],
            "submitter_email": body["submitter_email"],
            "s3_key": s3_key,
            "status": "PENDING",
            "decision_token": decision_token,
            "submitted_at": datetime.utcnow().isoformat(),
        })

        approve_link = f"{APP_BASE_URL}/decision?doc_id={doc_id}&token={decision_token}&action=approve"
        reject_link  = f"{APP_BASE_URL}/decision?doc_id={doc_id}&token={decision_token}&action=reject"

        sns.publish(
            TopicArn=TOPIC_ARN,
            Subject=f"Approval needed: {body['title']}"[:100],
            Message=(
                f"{body['submitter_name']} submitted a document for approval.\n\n"
                f"Title: {body['title']}\n\n"
                f"Approve: {approve_link}\n"
                f"Reject:  {reject_link}"
            ),
        )

        return _response(200, {"doc_id": doc_id, "message": "Document submitted and pending approval."})

    except Exception as e:
        print(f"ERROR: {e}")
        return _response(500, {"error": "Something went wrong. Please try again later."})


def _response(code, body):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": ALLOWED_ORIGIN},
        "body": json.dumps(body, ensure_ascii=False),
    }
