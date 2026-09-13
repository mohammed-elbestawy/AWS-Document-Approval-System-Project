<a id="top"></a>

# 🛠 Build Log — AWS Serverless Document Approval System

> Step-by-step record of the AWS resources configured for the document approval workflow.

## 📋 Quick Navigation

| Step | Section |
|---|---|
| 1 | [DynamoDB](#step-1) |
| 2 | [SNS](#step-2) |
| 3 | [IAM](#step-3) |
| 4 | [S3 Document Storage](#step-4) |
| 5 | [submit-handler](#step-5) |
| 6 | [decision-handler](#step-6) |
| 7 | [API Gateway](#step-7) |
| 8 | [Frontend / S3](#step-8) |
| 9 | [CloudFront + OAC](#step-9) |
| 10 | [Upload Frontend](#step-10) |
| 11 | [Final Environment Variables + CORS](#step-11) |
| 12 | [End-to-End Test](#step-12) |
| 13 | [Cleanup](#cleanup) |

<a id="step-1"></a>

---

## Step 1 — 🗃 DynamoDB

Create the table used for document metadata and approval state.

| Setting | Value |
|---|---|
| Table | `document-approvals` |
| Partition key | `doc_id` |
| Type | String |
| Capacity | On-demand |

Initial status:

```text
PENDING
```

![DynamoDB configuration](screenshots/01-dynamodb.png)

<a id="step-2"></a>

---

## Step 2 — 📣 SNS Topic & Subscription

Create the notification topic used to send approval emails.

```text
Topic: approval-notifications
Type: Standard
Protocol: Email
```

Confirm the email subscription before testing notifications.

![SNS topic configuration](screenshots/02-sns-topic.png)

<a id="step-3"></a>

---

## Step 3 — 🔐 IAM Role & Policy

Create the Lambda execution role and attach the required policy.

The role provides access to the AWS services used by the application:

- CloudWatch Logs
- S3
- DynamoDB
- SNS

Use least privilege and scope resource ARNs where supported.

![IAM role configuration](screenshots/03-iam-role.png)

<a id="step-4"></a>

---

## Step 4 — 🪣 S3 Document Storage

Create the private S3 bucket used to store uploaded PDF documents.

The bucket should not be publicly readable.

![S3 storage configuration](screenshots/04-s3-storage.png)

<a id="step-5"></a>

---

## Step 5 — ⚡ `submit-handler`

Create the Lambda function responsible for receiving and processing a new document submission.

```text
Runtime: Python 3.12
Function: submit-handler
```

### Main responsibility

```text
Validate request
      ↓
Store PDF in S3
      ↓
Create DynamoDB record
      ↓
PENDING
      ↓
Publish SNS approval email
```

### Environment variables

```text
TABLE_NAME
TOPIC_ARN
APP_BASE_URL
ALLOWED_ORIGIN
```

![submit-handler configuration](screenshots/05-lambda-submit-config.png)

<a id="step-6"></a>

---

## Step 6 — ⚡ `decision-handler`

Create the Lambda function responsible for processing the Approve / Reject link.

```text
Runtime: Python 3.12
Function: decision-handler
```

Expected query parameters:

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

The function validates the token and current status before updating DynamoDB.

![decision-handler configuration](screenshots/06-lambda-decision-config.png)

<a id="step-7"></a>

---

## Step 7 — 🔌 API Gateway

Create the REST API used by the frontend and approval links.

### Routes

```text
POST /submit
GET  /decision
```

Connect each route to its corresponding Lambda function.

The API Gateway Invoke URL is later used as `APP_BASE_URL`.

![API Gateway configuration](screenshots/07-apigateway-invoke.png)

<a id="step-8"></a>

---

## Step 8 — 🌐 Frontend S3 Bucket

Create/use the S3 bucket that contains the static frontend files:

```text
index.html
style.css
script.js
```

The frontend bucket is kept private and is intended to be accessed through CloudFront.

<a id="step-9"></a>

---

## Step 9 — 🌍 CloudFront + OAC

Create a CloudFront distribution for the frontend.

### Origin

Select:

```text
Amazon S3
```

Choose the frontend S3 bucket as the origin.

### Origin access

Select:

```text
Allow private S3 bucket access to CloudFront
```

This creates/uses **Origin Access Control (OAC)** so CloudFront can read the private bucket.

---

### Origin settings

Use the recommended settings for S3 unless the project requires a custom configuration.

---

### Important viewer setting

Use:

```text
Redirect HTTP to HTTPS
```

---

### Default root object

Set:

```text
index.html
```

![CloudFront distribution](screenshots/09-cloudfront-distribution.png)

---

### S3 bucket policy

CloudFront/OAC should be the trusted path to the private frontend bucket.

![S3 bucket policy](screenshots/09-s3-bucket-policy.png)

<a id="step-10"></a>

---

## Step 10 — 📤 Upload Frontend

Upload the frontend files to the frontend S3 bucket.

The main file is:

```text
index.html
```

Do not make the bucket public just to display the website. CloudFront + OAC is the intended access path.

<a id="step-11"></a>

---

## Step 11 — 🔧 Final `APP_BASE_URL` + CORS

After CloudFront is created, update the `submit-handler` environment variables.

### `APP_BASE_URL`

Set it to the **API Gateway Invoke URL** because the generated approval links point to:

```text
/decision
```

Example:

```text
APP_BASE_URL=https://<api-id>.execute-api.<region>.amazonaws.com/<stage>
```

### `ALLOWED_ORIGIN`

Set it to the real CloudFront domain because this value controls browser CORS.

```text
ALLOWED_ORIGIN=https://<distribution-id>.cloudfront.net
```

![Final Lambda environment variables](screenshots/11-lambda-env-updated.png)

<a id="step-12"></a>

---

## Step 12 — ✅ End-to-End Test

Test the complete workflow in order.

---

### 12.1 Submit the PDF

Open the CloudFront URL and submit a small test PDF.

![Full test — submit](screenshots/12-fulltest-submit.png)

---

### 12.2 Check the approval email

Confirm the approver receives the email with the decision links.

![Full test — approval email](screenshots/12-fulltest-approval-email.png)

---

### 12.3 Open Approve / Reject

Click the approval link and verify that the decision page is returned.

![Full test — decision page](screenshots/12-fulltest-decision-page.png)

---

### 12.4 Verify DynamoDB

The document status should change from:

```text
PENDING
```

to:

```text
APPROVED
```

or:

```text
REJECTED
```

![Full test — DynamoDB status](screenshots/12-fulltest-dynamodb-status.png)

---

### Expected result

```text
Frontend
   ↓
API Gateway
   ↓
submit-handler
   ↓
S3 + DynamoDB + SNS
   ↓
Approval Email
   ↓
/decision
   ↓
decision-handler
   ↓
DynamoDB status updated
```

<a id="cleanup"></a>


---

<div align="center">

[⬆️ Back to top](#top)

</div>
