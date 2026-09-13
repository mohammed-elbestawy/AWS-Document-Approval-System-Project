<a id="top"></a>

# 🛠 Build Log — AWS Serverless Document Approval System

> A step-by-step record of the resources created and configured for the document approval workflow.

## 📋 Quick Navigation

| Step | Section |
|---|---|
| 1 | [🗃 DynamoDB Table](#step-1) |
| 2 | [📣 SNS Topic & Subscription](#step-2) |
| 3 | [🔐 IAM Role & Policy](#step-3) |
| 4 | [⚡ `submit-handler`](#step-4) |
| 5 | [⚡ `decision-handler`](#step-5) |
| 6 | [🔌 API Gateway](#step-6) |
| 7 | [🔗 Configure `APP_BASE_URL`](#step-7) |
| 8 | [🪣 Frontend S3 Bucket](#step-8) |
| 9 | [🌍 CloudFront + OAC](#step-9) |
| 10 | [📤 Upload Frontend](#step-10) |
| 11 | [🔒 Final `APP_BASE_URL` + CORS](#step-11) |
| 12 | [✅ End-to-End Test](#step-12) |
| 13 | [🧹 Cleanup](#cleanup) |

---

<a id="step-1"></a>

## Step 1 — 🗃 DynamoDB Table

Create the table used to store document metadata and workflow state.

### Configuration

| Setting | Value |
|---|---|
| Table name | `document-approvals` |
| Partition key | `doc_id` |
| Key type | String |
| Capacity mode | On-demand |

The initial workflow status is:

```text
PENDING
```

### Why?

DynamoDB is used because the application mainly needs fast key-based access to a document record and simple status updates.

📸 Screenshot:

[`screenshots/01-dynamodb.png`](screenshots/01-dynamodb.png)

---

<a id="step-2"></a>

## Step 2 — 📣 SNS Topic & Subscription

Create the SNS topic used for approval notifications.

### Configuration

```text
Topic name:
approval-notifications
```

Use:

```text
Type: Standard
Protocol: Email
```

Confirm the subscription from the AWS email.

### Why?

SNS provides a managed notification layer:

```text
Lambda
   ↓
SNS
   ↓
Email
```

📸 Screenshot:

[`screenshots/02-sns-topic.png`](screenshots/02-sns-topic.png)

---

<a id="step-3"></a>

## Step 3 — 🔐 IAM Role & Policy

Create the Lambda execution role:

```text
document-approval-lambda-role
```

Create/attach the project policy:

```text
document-approval-lambda-policy
```

The role needs the permissions required by the Lambda functions, including:

- CloudWatch Logs
- DynamoDB access
- S3 access
- SNS publish

Follow least privilege and scope resource ARNs where supported.

📸 Screenshot:

[`screenshots/03-iam-role.png`](screenshots/03-iam-role.png)

---

<a id="step-4"></a>

## Step 4 — ⚡ `submit-handler`

Create the Lambda function:

```text
submit-handler
```

### Runtime

```text
Python 3.12
```

### Execution role

```text
document-approval-lambda-role
```

### Environment variables

```text
TABLE_NAME
TOPIC_ARN
APP_BASE_URL
ALLOWED_ORIGIN
```

At this point `APP_BASE_URL` will eventually be the API Gateway Invoke URL.

### Responsibility

The function handles the submission workflow:

```text
Validate
   ↓
Store PDF in S3
   ↓
Create DynamoDB record
   ↓
PENDING
   ↓
Publish SNS notification
```

📸 Screenshot:

[`screenshots/04-lambda-submit-config.png`](screenshots/04-lambda-submit-config.png)

---

<a id="step-5"></a>

## Step 5 — ⚡ `decision-handler`

Create:

```text
decision-handler
```

### Runtime

```text
Python 3.12
```

### Execution role

```text
document-approval-lambda-role
```

### Environment variables

```text
TABLE_NAME
TOPIC_ARN
```

### Expected query parameters

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

### Decision flow

```text
Request
  ↓
Validate parameters
  ↓
Read DynamoDB
  ↓
Validate token
  ↓
Check status == PENDING
  ↓
Update status
  ↓
Return HTML confirmation
```

📸 Screenshot:

[`screenshots/05-lambda-decision-config.png`](screenshots/05-lambda-decision-config.png)

---

<a id="step-6"></a>

## Step 6 — 🔌 API Gateway

Create a:

```text
REST API
```

Name:

```text
document-approval-api
```

Endpoint type:

```text
Regional
```

### Resource 1 — `/submit`

Create:

```text
POST /submit
```

Integration:

```text
Lambda proxy
→ submit-handler
```

Enable CORS for the frontend flow.

### Resource 2 — `/decision`

Create:

```text
GET /decision
```

Integration:

```text
Lambda proxy
→ decision-handler
```

The approval/rejection URL is opened directly from an email, so this endpoint returns the HTML decision result.

### Deploy

Create a stage:

```text
prod
```

Copy the Invoke URL.

Example:

```text
https://<api-id>.execute-api.eu-north-1.amazonaws.com/prod
```

📸 Screenshot:

[`screenshots/06-apigateway-invoke.png`](screenshots/06-apigateway-invoke.png)

---

<a id="step-7"></a>

## Step 7 — 🔗 Configure `APP_BASE_URL`

Go to:

```text
Lambda
→ submit-handler
→ Configuration
→ Environment variables
```

Set:

```text
APP_BASE_URL =
https://<api-id>.execute-api.eu-north-1.amazonaws.com/prod
```

### Important

Do **not** use the CloudFront URL here.

The approval link must point to:

```text
/decision
```

and `/decision` is handled by API Gateway.

---

<a id="step-8"></a>

## Step 8 — 🪣 Frontend S3 Bucket

Create a dedicated S3 bucket for the frontend.

Example:

```text
document-approval-frontend-<account-id>
```

Use the same AWS region as the project:

```text
eu-north-1
```

### Security

Keep:

```text
Block all public access = ON
```

Do not make the bucket public.

### Upload

Upload the frontend files, including:

```text
index.html
```

and any CSS/JavaScript/assets used by the project.

📸 Screenshot:

[`screenshots/08-s3-bucket.png`](screenshots/08-s3-bucket.png)

---

<a id="step-9"></a>

## Step 9 — 🌍 CloudFront + OAC

This uses the **current CloudFront distribution creation flow**.

Go to:

```text
CloudFront
→ Distributions
→ Create distribution
```

### 9.1 Origin type

Choose:

```text
Amazon S3
```

Select the frontend S3 bucket.

### 9.2 Private S3 access

Enable:

```text
Allow private S3 bucket access to CloudFront
```

This creates/uses:

```text
Origin Access Control (OAC)
```

The bucket remains private.

### 9.3 Origin settings

Use:

```text
Use recommended origin settings
```

for the normal S3 static frontend configuration.

### 9.4 Viewer protocol

Use:

```text
Redirect HTTP to HTTPS
```

### 9.5 Allowed methods

For the static frontend:

```text
GET
HEAD
```

The form's `POST /submit` request goes to **API Gateway**, not to the CloudFront S3 origin.

### 9.6 Default root object

Set:

```text
index.html
```

### 9.7 Create distribution

Create the distribution and wait until it becomes deployed.

Copy the CloudFront domain:

```text
https://<distribution-id>.cloudfront.net
```

### 9.8 S3 bucket policy

If CloudFront provides a generated S3 bucket policy, apply it to the frontend bucket under:

```text
S3
→ Bucket
→ Permissions
→ Bucket policy
```

The policy should allow the CloudFront distribution to read the objects while the bucket remains private.

📸 Screenshots:

[`screenshots/09-cloudfront-distribution.png`](screenshots/09-cloudfront-distribution.png)

[`screenshots/09-s3-bucket-policy.png`](screenshots/09-s3-bucket-policy.png)

---

<a id="step-10"></a>

## Step 10 — 📤 Upload / Verify Frontend

Make sure the frontend is configured to call:

```text
<API_GATEWAY_URL>/submit
```

Upload the final frontend files to S3.

Then open:

```text
https://<distribution-id>.cloudfront.net
```

Verify:

```text
Frontend loads
HTTPS works
CSS/JavaScript load
```

---

<a id="step-11"></a>

## Step 11 — 🔒 Final `APP_BASE_URL` + CORS

Return to:

```text
Lambda
→ submit-handler
→ Configuration
→ Environment variables
```

### `APP_BASE_URL`

Set:

```text
APP_BASE_URL =
<API Gateway Invoke URL>
```

Example:

```text
https://<api-id>.execute-api.eu-north-1.amazonaws.com/prod
```

### `ALLOWED_ORIGIN`

Set:

```text
ALLOWED_ORIGIN =
https://<distribution-id>.cloudfront.net
```

### Remember the difference

```text
APP_BASE_URL
      ↓
API Gateway
      ↓
/decision
```

while:

```text
ALLOWED_ORIGIN
      ↓
CloudFront
      ↓
Browser CORS
```

📸 Screenshot:

[`screenshots/11-lambda-env-updated.png`](screenshots/11-lambda-env-updated.png)

---

<a id="step-12"></a>

## Step 12 — ✅ End-to-End Test

### Test 1 — Open the application

Open:

```text
https://<distribution-id>.cloudfront.net
```

Expected:

```text
Frontend loads successfully
```

📸

[`screenshots/12-fulltest-submit.png`](screenshots/12-fulltest-submit.png)

### Test 2 — Submit a small PDF

Submit a test document.

Expected:

```text
Submission successful
```

### Test 3 — Check DynamoDB

Open:

```text
document-approvals
```

Expected:

```text
status = PENDING
```

### Test 4 — Check approver email

The approver should receive an email containing:

```text
Approve
Reject
```

📸

[`screenshots/12-fulltest-approval-email.png`](screenshots/12-fulltest-approval-email.png)

### Test 5 — Approve

Click the Approve link.

Expected flow:

```text
Email
  ↓
API Gateway /decision
  ↓
decision-handler
  ↓
DynamoDB
  ↓
APPROVED
```

The browser should show a simple confirmation HTML page.

📸

[`screenshots/12-fulltest-decision-page.png`](screenshots/12-fulltest-decision-page.png)

### Test 6 — Verify DynamoDB

Expected:

```text
PENDING → APPROVED
```

For Reject:

```text
PENDING → REJECTED
```

📸

[`screenshots/12-fulltest-dynamodb-status.png`](screenshots/12-fulltest-dynamodb-status.png)

### Test 7 — Verify notification

Confirm the configured SNS notification flow sends the decision result.

---

<a id="cleanup"></a>

## Step 13 — 🧹 Cleanup

Serverless does **not** mean permanently free.

If the project is no longer needed, remove resources carefully.

Recommended order:

1. Disable/delete the CloudFront distribution after it is disabled.
2. Empty and delete the frontend S3 bucket.
3. Empty and delete the document S3 bucket.
4. Delete the API Gateway.
5. Delete the Lambda functions.
6. Delete the DynamoDB table.
7. Delete the SNS topic/subscriptions.
8. Delete the IAM role/policy if they are no longer used.

> Keep the project resources if you are still actively demonstrating or testing it, but monitor AWS Billing/Cost Explorer.

---

<div align="center">

[⬆️ Back to top](#top)

</div>
