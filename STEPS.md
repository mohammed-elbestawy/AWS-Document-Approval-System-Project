# Build Log — AWS Document Approval System

A step-by-step record of the resources created for the serverless document approval workflow.

## Quick Navigation

| Step | Section |
|---|---|
| 1 | DynamoDB |
| 2 | SNS |
| 3 | IAM |
| 4 | `submit-handler` |
| 5 | `decision-handler` |
| 6 | API Gateway |
| 7 | Temporary `APP_BASE_URL` |
| 8 | Frontend S3 |
| 9 | CloudFront + OAC |
| 10 | Frontend Upload |
| 11 | Final `APP_BASE_URL` + CORS |
| 12 | End-to-End Test |

---

## Step 1 — DynamoDB Table

Create the table:

```text
document-approvals
```

Settings:

| Setting | Value |
|---|---|
| Partition key | `doc_id` |
| Type | String |
| Capacity | On-demand |

The initial document state is:

```text
PENDING
```

Screenshot: `screenshots/01-dynamodb.png`

---

## Step 2 — SNS Topic & Subscription

Create:

```text
approval-notifications
```

Settings:

- Type: Standard
- Protocol: Email
- Endpoint: approver email
- Confirm the subscription from the AWS email.

Save the Topic ARN because the Lambda functions use it through `TOPIC_ARN`.

Screenshot: `screenshots/02-sns-topic.png`

---

## Step 3 — IAM Policy & Role

Create an IAM policy:

```text
document-approval-lambda-policy
```

The execution role must provide the permissions required by the Lambda functions:

- CloudWatch Logs
- DynamoDB access to `document-approvals`
- S3 access required for document storage
- SNS publish

Then create:

```text
document-approval-lambda-role
```

Trusted entity:

```text
AWS service → Lambda
```

Attach the policy to the role.

Screenshot: `screenshots/03-iam-role.png`

> Keep resource ARNs scoped to the actual resources whenever the AWS service supports resource-level permissions.

---

## Step 4 — Lambda: `submit-handler`

Create a Lambda function:

```text
submit-handler
```

Runtime:

```text
Python 3.12
```

Execution role:

```text
document-approval-lambda-role
```

Deploy the project `submit-handler` code.

Environment variables:

| Key | Value |
|---|---|
| `TABLE_NAME` | `document-approvals` |
| `TOPIC_ARN` | SNS Topic ARN |
| `APP_BASE_URL` | API Gateway Invoke URL |
| `ALLOWED_ORIGIN` | CloudFront domain |

Timeout:

```text
15 seconds
```

The function handles the submission and creates the approval workflow.

Screenshot: `screenshots/04-lambda-submit-config.png`

---

## Step 5 — Lambda: `decision-handler`

Create:

```text
decision-handler
```

Runtime:

```text
Python 3.12
```

Role:

```text
document-approval-lambda-role
```

Environment variables:

| Key | Value |
|---|---|
| `TABLE_NAME` | `document-approvals` |
| `TOPIC_ARN` | SNS Topic ARN |

Timeout:

```text
15 seconds
```

The function receives:

```text
doc_id
token
action
```

Allowed actions:

```text
approve
reject
```

The important authorization check is:

```python
if item.get("decision_token") != token:
    return _html_response(403, "Invalid or expired approval link.")
```

It also checks that the current status is `PENDING` before updating the document.

Screenshot: `screenshots/05-lambda-decision-config.png`

---

## Step 6 — API Gateway

Create:

```text
document-approval-api
```

Type:

```text
REST API
```

Endpoint type:

```text
Regional
```

### `/submit`

- Resource: `submit`
- Method: `POST`
- Lambda proxy integration
- Lambda: `submit-handler`
- Enable CORS

### `/decision`

- Resource: `decision`
- Method: `GET`
- Lambda proxy integration
- Lambda: `decision-handler`

The decision link is opened directly by the browser, so it does not use the frontend JavaScript CORS flow.

### Deploy

Create stage:

```text
prod
```

Copy the Invoke URL.

Example:

```text
https://<api-id>.execute-api.eu-north-1.amazonaws.com/prod
```

Screenshot: `screenshots/06-apigateway-invoke.png`

---

## Step 7 — Temporary `APP_BASE_URL`

Before finalizing the frontend, configure:

**Lambda → `submit-handler` → Configuration → Environment variables**

Set:

```text
APP_BASE_URL = <API Gateway Invoke URL>
```

The approval links must point to API Gateway because `/decision` is an API endpoint.

---

## Step 8 — S3 Frontend Bucket

Create:

```text
document-approval-frontend-<account-id>
```

Region:

```text
eu-north-1
```

Security:

```text
Block all public access = ON
```

Upload the frontend files, including:

```text
index.html
```

Do not make the bucket public.

Screenshot: `screenshots/08-s3-bucket.png`

---

## Step 9 — CloudFront + OAC

Use the current CloudFront distribution workflow.

1. Open **CloudFront → Distributions → Create distribution**.
2. Origin type: **Amazon S3**.
3. Select the frontend S3 bucket.
4. Enable:

```text
Allow private S3 bucket access to CloudFront
```

This configures Origin Access Control (OAC).

### Origin settings

Use:

```text
Use recommended origin settings
```

### Cache / viewer settings

For a normal static frontend:

```text
Viewer protocol policy: Redirect HTTP to HTTPS
Allowed methods: GET, HEAD
```

### Default root object

Set:

```text
index.html
```

For this learning project, leave additional WAF protections disabled unless you intentionally decide to add them.

Create the distribution and wait for deployment.

Copy the CloudFront domain:

```text
https://<distribution-id>.cloudfront.net
```

If CloudFront provides a generated S3 bucket policy, copy it to:

**S3 → Bucket → Permissions → Bucket policy**

The bucket remains private.

Screenshots:

```text
screenshots/09-cloudfront-distribution.png
screenshots/09-s3-bucket-policy.png
```

---

## Step 10 — Frontend Upload

Make sure the frontend uses the real API Gateway URL.

The browser sends:

```text
POST <API_GATEWAY_URL>/submit
```

Upload the updated frontend files to the private S3 bucket.

Then open:

```text
https://<distribution-id>.cloudfront.net
```

Confirm the frontend loads through CloudFront.

---

## Step 11 — Final `APP_BASE_URL` & CORS

Open:

**Lambda → `submit-handler` → Configuration → Environment variables**

Set:

```text
APP_BASE_URL = <API Gateway Invoke URL>
```

Important:

> `APP_BASE_URL` is the API Gateway Invoke URL, not the CloudFront URL. The approval links target `/decision`, which is an API Gateway endpoint.

Set:

```text
ALLOWED_ORIGIN = https://<distribution-id>.cloudfront.net
```

Use the real CloudFront domain.

Screenshot:

```text
screenshots/11-lambda-env-updated.png
```

---

## Step 12 — End-to-End Test

### 1. Open the frontend

Open the CloudFront URL.

### 2. Submit a small PDF

Fill in the required information and submit the document.

### 3. Check DynamoDB

Open:

```text
document-approvals
```

Confirm:

```text
status = PENDING
```

### 4. Check the approver email

Confirm the email contains:

```text
Approve
Reject
```

### 5. Click Approve

The flow is:

```text
Email Link
  ↓
API Gateway /decision
  ↓
decision-handler
  ↓
DynamoDB
```

The browser should display a simple HTML confirmation page.

### 6. Check DynamoDB again

Confirm:

```text
PENDING → APPROVED
```

For rejection:

```text
PENDING → REJECTED
```

### 7. Check the result notification

Confirm the configured SNS notification path sends the decision result.

Screenshots:

```text
screenshots/12-fulltest-submit.png
screenshots/12-fulltest-approval-email.png
screenshots/12-fulltest-decision-page.png
screenshots/12-fulltest-dynamodb-status.png
```

---

## Cleanup

Although the architecture is serverless, serverless does not mean permanently free.

If the project is no longer needed, delete the resources manually:

1. CloudFront distribution
2. S3 frontend bucket
3. S3 document bucket
4. API Gateway
5. Lambda functions
6. DynamoDB table
7. SNS topic/subscriptions
8. IAM role/policy if no longer used
