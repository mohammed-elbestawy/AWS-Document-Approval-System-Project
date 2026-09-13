<a id="top"></a>

# 🛠 Build Log — AWS Serverless Document Approval System

> A step-by-step record of the resources created and the configuration used to build the document approval workflow.

---

## 📋 Quick Navigation

| Step | Section |
|---:|---|
| 01 | 🗃 [DynamoDB](#step-1) |
| 02 | 📣 [SNS Topic & Subscription](#step-2) |
| 03 | 🔐 [IAM Role & Policy](#step-3) |
| 04 | 🪣 [S3 Document Storage](#step-4) |
| 05 | ⚡ [submit-handler](#step-5) |
| 06 | ⚡ [decision-handler](#step-6) |
| 07 | 🔌 [API Gateway](#step-7) |
| 08 | 🌐 [Frontend S3 Bucket](#step-8) |
| 09 | 🌍 [CloudFront + OAC](#step-9) |
| 10 | 📤 [Upload Frontend](#step-10) |
| 11 | 🔧 [Final Environment Variables + CORS](#step-11) |
| 12 | ✅ [End-to-End Test](#step-12) |

---

<a id="step-1"></a>

## Step 1 — 🗃 DynamoDB

Create the table used to store document metadata and approval state.

```text
Table: document-approvals
Partition key: doc_id
Type: String
Capacity mode: On-demand
```

Initial approval state:

```text
PENDING
```

![DynamoDB configuration](screenshots/01-dynamodb.png)

---

<a id="step-2"></a>

## Step 2 — 📣 SNS Topic & Subscription

Create the SNS topic used for approval notifications.

```text
Topic: approval-notifications
Type: Standard
Protocol: Email
```

Confirm the email subscription before testing notifications.

![SNS topic configuration](screenshots/02-sns-topic.png)

---

<a id="step-3"></a>

## Step 3 — 🔐 IAM Role & Policy

Create the Lambda execution role and attach the permissions required by the application.

The role is used for access to:

- CloudWatch Logs
- S3
- DynamoDB
- SNS

Keep permissions limited to the resources and actions required by the functions.

![IAM role configuration](screenshots/03-iam-role.png)

---

<a id="step-4"></a>

## Step 4 — 🪣 S3 Document Storage

Create the private S3 bucket used to store uploaded PDF documents.

The document bucket should not be publicly readable.

![S3 storage configuration](screenshots/04-s3-storage.png)

---

<a id="step-5"></a>

## Step 5 — ⚡ `submit-handler`

Create the Lambda function responsible for receiving a new document submission.

```text
Function: submit-handler
Runtime: Python 3.12
```

### Processing flow

```text
Validate request
      ↓
Store PDF in S3
      ↓
Create DynamoDB record
      ↓
Set status = PENDING
      ↓
Publish SNS approval notification
```

### Environment variables

```text
TABLE_NAME
TOPIC_ARN
APP_BASE_URL
ALLOWED_ORIGIN
```

![submit-handler configuration](screenshots/05-lambda-submit-config.png)

---

<a id="step-6"></a>

## Step 6 — ⚡ `decision-handler`

Create the Lambda function responsible for processing the approval decision.

```text
Function: decision-handler
Runtime: Python 3.12
```

The request contains:

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

The function validates the document, token, action and current state before updating DynamoDB.

![decision-handler configuration](screenshots/06-lambda-decision-config.png)

---

<a id="step-7"></a>

## Step 7 — 🔌 API Gateway

Create the REST API used by the frontend and approval links.

### Routes

```text
POST /submit
GET  /decision
```

Connect each route to its corresponding Lambda function.

The API Gateway Invoke URL is used as the base URL for the approval links.

![API Gateway configuration](screenshots/07-apigateway-invoke.png)

---

<a id="step-8"></a>

## Step 8 — 🌐 Frontend S3 Bucket

Create/use the S3 bucket that contains the static frontend files.

```text
index.html
style.css
script.js
```

Keep the bucket private. The public entry point will be CloudFront.

---

<a id="step-9"></a>

## Step 9 — 🌍 CloudFront + Origin Access Control

Create a CloudFront distribution for the frontend.

### 9.1 Origin type

Select:

```text
Amazon S3
```

Then choose the frontend S3 bucket.

### 9.2 Private S3 access — current CloudFront setup

Under the S3 origin settings, enable:

```text
Allow private S3 bucket access to CloudFront
```

This uses **Origin Access Control (OAC)** and allows CloudFront to read from the private S3 bucket.

### 9.3 Origin settings

Use:

```text
Use recommended origin settings
```

for the S3 origin unless a project-specific customization is required.

### 9.4 Cache settings

Use:

```text
Use recommended cache settings tailored to serving S3 content
```

### 9.5 Viewer protocol

Set the viewer protocol policy to:

```text
Redirect HTTP to HTTPS
```

### 9.6 Default root object

Set:

```text
index.html
```

This makes the CloudFront distribution open the frontend automatically.

![CloudFront distribution](screenshots/09-cloudfront-distribution.png)

### 9.7 S3 bucket policy

CloudFront/OAC should be the trusted path for reading the private frontend bucket.

![S3 bucket policy](screenshots/09-s3-bucket-policy.png)

---

<a id="step-10"></a>

## Step 10 — 📤 Upload Frontend

Upload the frontend files to the frontend S3 bucket.

The main entry file is:

```text
index.html
```

Also upload:

```text
style.css
script.js
```

Do not make the bucket public just to display the website. CloudFront + OAC is the intended access path.

---

<a id="step-11"></a>

## Step 11 — 🔧 Final `APP_BASE_URL` + CORS

After the API Gateway and CloudFront URLs are available, update the Lambda environment variables.

### `APP_BASE_URL`

Set this to the **API Gateway Invoke URL**.

The reason is that the generated approval links point to the API endpoint:

```text
/decision
```

Example:

```text
APP_BASE_URL=https://<api-id>.execute-api.<region>.amazonaws.com/<stage>
```

### `ALLOWED_ORIGIN`

Set this to the actual CloudFront domain because it represents the browser origin allowed to call the API.

Example:

```text
ALLOWED_ORIGIN=https://<distribution-id>.cloudfront.net
```

![Final Lambda environment variables](screenshots/11-lambda-env-updated.png)

---

<a id="step-12"></a>

---

## Step 12 — ✅ End-to-End Test

Test the workflow from beginning to end.

---

### 12.1 Submit the PDF

Open the CloudFront URL and submit a small test PDF.

![Full test — submit](screenshots/12-fulltest-submit.png)

---

### 12.2 Open the decision link

Click **Approve** or **Reject** and verify that the decision page is returned.

![Full test — decision page](screenshots/12-fulltest-decision-page.png)

---

### 12.3 Verify DynamoDB

The document status should move from:

```text
PENDING
```

to either:

```text
APPROVED
```

or:

```text
REJECTED
```

![Full test — DynamoDB status](screenshots/12-fulltest-dynamodb-status.png)

---

### 12.4 Verify S3


![Full test — S3 Page](screenshots/12-fulltest-S3.png)

---

<div align="center">

[⬆️ Back to top](#top)

</div>
