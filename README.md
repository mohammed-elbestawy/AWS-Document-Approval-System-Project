<a id="top"></a>

# 📄 AWS Serverless Document Approval System

> A fully serverless AWS workflow for submitting PDF documents, notifying an approver by email, and processing **Approve / Reject** decisions through secure API links.

![AWS](https://img.shields.io/badge/AWS-Serverless-FF9900?style=flat&logo=amazonaws&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![Architecture](https://img.shields.io/badge/Architecture-Serverless-blue)
![Status](https://img.shields.io/badge/Status-Tested-brightgreen)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [How the workflow works](#workflow)
- [AWS Services](#services)
- [Security](#security)
- [Approval mechanism](#approval)
- [API](#api)
- [Project Structure](#structure)
- [End-to-End Test](#test)
- [Documentation](#documentation)
- [Possible Improvements](#improvements)
- [Cost Management](#cost)
- [Back to top](#top)

---

<a id="overview"></a>

## 🎯 Overview

The project implements a serverless document approval workflow on AWS.

A user accesses the web application through **CloudFront**, submits a PDF, and the backend processes the request through **API Gateway** and **Lambda**.

The document workflow is then connected to:

- **Amazon S3** for private document storage
- **Amazon DynamoDB** for document metadata and approval status
- **Amazon SNS** for email notifications
- **AWS IAM** for permissions
- **Amazon CloudFront + OAC** for secure HTTPS frontend delivery

There is no EC2 instance or traditional application server.

### Main workflow

```text
User
  │
  ▼
CloudFront
  │
  ▼
Private S3
  │
  ▼
Frontend
  │
  │ POST /submit
  ▼
API Gateway
  │
  ▼
submit-handler Lambda
  ├──────────────► S3
  │                 └─ PDF document
  │
  ├──────────────► DynamoDB
  │                 └─ PENDING
  │
  └──────────────► SNS
                    └─ Approver email
                           │
                           ▼
                    Approve / Reject
                           │
                           ▼
                    GET /decision
                           │
                           ▼
                    API Gateway
                           │
                           ▼
                 decision-handler Lambda
                     │          │
                     ▼          ▼
                 DynamoDB      SNS
               APPROVED/      Result
               REJECTED       notification
```

---

<a id="architecture"></a>

## 🏗 Architecture

![Architecture Diagram](screenshots/architecture-diagram.png)

> **Architecture diagram:** [`screenshots/architecture-diagram.png`](screenshots/architecture-diagram.png)

### Architecture layers

| Layer | AWS Service | Responsibility |
|---|---|---|
| Frontend delivery | Amazon S3 + CloudFront | Hosts and securely delivers the static frontend |
| S3 security | CloudFront OAC | Allows CloudFront to access the private S3 bucket |
| API | API Gateway | Exposes `/submit` and `/decision` |
| Compute | AWS Lambda | Processes submission and approval decisions |
| Document storage | Amazon S3 | Stores submitted PDF documents |
| Database | DynamoDB | Stores metadata, token and status |
| Notifications | SNS | Sends approval/result emails |
| Permissions | IAM | Controls Lambda access to AWS resources |

**Primary deployment region:** `eu-north-1`

---

<a id="workflow"></a>

## 🔄 How the Workflow Works

### 1. User opens the application

The user opens the **CloudFront HTTPS URL**.

CloudFront serves the static frontend from the private S3 bucket.

### 2. User submits a PDF

The frontend sends the submission to:

```text
POST /submit
```

through API Gateway.

### 3. `submit-handler` processes the request

The Lambda function:

1. Validates the request.
2. Generates/uses the document identifier and approval token.
3. Stores the PDF in S3.
4. Creates the DynamoDB record.
5. Sets the initial status to:

```text
PENDING
```

6. Publishes the approval notification through SNS.

### 4. Approver receives an email

The email contains approval links similar to:

```text
Approve → /decision?doc_id=...&token=...&action=approve

Reject  → /decision?doc_id=...&token=...&action=reject
```

### 5. Approver clicks a decision

The browser opens:

```text
GET /decision
```

API Gateway invokes `decision-handler`.

### 6. `decision-handler` validates the request

The Lambda checks:

- `doc_id`
- `token`
- `action`
- current document status

The action must be one of:

```text
approve
reject
```

The document must still be:

```text
PENDING
```

### 7. Status is updated

The state changes to:

```text
PENDING
   │
   ├── Approve → APPROVED
   │
   └── Reject  → REJECTED
```

### 8. Result notification

The final decision is published through SNS according to the configured notification flow.

---

<a id="services"></a>

## ☁️ AWS Services

### 🪣 Amazon S3

Two storage responsibilities are separated:

```text
Frontend S3
→ index.html / CSS / JavaScript

Documents S3
→ uploaded PDF documents
```

The frontend bucket is private and accessed through CloudFront OAC.

The document bucket is also kept private.

### 🌍 Amazon CloudFront

CloudFront is the public HTTPS entry point for the static frontend.

Important configuration:

- S3 origin
- Origin Access Control (OAC)
- Private S3 bucket
- Redirect HTTP → HTTPS
- Default root object: `index.html`

### 🔌 API Gateway

The API provides:

```text
POST /submit
GET  /decision
```

It acts as the HTTP layer between the browser and Lambda.

### ⚡ AWS Lambda

The project separates responsibilities into:

```text
submit-handler
decision-handler
```

### 🗃 DynamoDB

Stores document information and workflow state.

Example logical record:

```text
doc_id
status
decision_token
...
```

The main state is:

```text
PENDING
APPROVED
REJECTED
```

### 📣 SNS

SNS is used for email notifications.

Main concept:

```text
Lambda
  ↓
SNS Topic
  ↓
Email Subscription
```

### 🔐 IAM

Lambda uses an IAM execution role with permissions required to interact with:

- S3
- DynamoDB
- SNS
- CloudWatch Logs

Permissions should follow least privilege wherever the AWS service supports resource-level restriction.

---

<a id="security"></a>

## 🔐 Security

The project applies several security controls.

### Private S3 frontend

The frontend bucket does **not** need to be public.

```text
Internet
   ↓
CloudFront
   ↓
OAC
   ↓
Private S3
```

This prevents normal users from bypassing CloudFront and accessing the frontend objects directly through S3.

### HTTPS

CloudFront redirects HTTP requests to HTTPS.

### CORS

The backend uses the actual CloudFront origin instead of:

```text
*
```

The idea is:

```text
ALLOWED_ORIGIN
=
https://<cloudfront-domain>
```

### Input validation

The Lambda validates incoming data before processing it.

### Approval token

The decision URL requires a document ID **and** the corresponding approval token.

Knowing only the document ID is not sufficient to make a decision.

### Status validation

A decision is processed only while the document is:

```text
PENDING
```

This prevents the normal workflow from repeatedly changing an already decided document.

### Generic client errors

Detailed internal errors should be logged to CloudWatch rather than returned directly to the browser.

---

<a id="approval"></a>

## 🔑 Approval Mechanism

The project uses a per-document token rather than requiring a full Cognito login for this simple approval workflow.

Conceptually:

```text
DynamoDB
┌──────────────────────────────┐
│ doc_id                       │
│ decision_token               │
│ status = PENDING             │
└──────────────────────────────┘
              ▲
              │ compare
              │
Email URL
┌──────────────────────────────┐
│ doc_id                        │
│ token                         │
│ action = approve/reject       │
└──────────────────────────────┘
```

If the token does not match, the request is rejected.

For a larger multi-user production system, authenticated identities such as Cognito would be a stronger direction.

---

<a id="api"></a>

## 🔌 API

### `POST /submit`

Used by the frontend to submit a document approval request.

```text
POST <API_GATEWAY_URL>/submit
```

### `GET /decision`

Used by the approval email links.

```text
GET <API_GATEWAY_URL>/decision?doc_id=<ID>&token=<TOKEN>&action=approve
```

or:

```text
GET <API_GATEWAY_URL>/decision?doc_id=<ID>&token=<TOKEN>&action=reject
```

### Important environment variables

#### `submit-handler`

```text
TABLE_NAME
TOPIC_ARN
APP_BASE_URL
ALLOWED_ORIGIN
```

`APP_BASE_URL` is the **API Gateway Invoke URL**, because the generated approval links target `/decision`.

`ALLOWED_ORIGIN` is the **CloudFront domain**, because it is used for browser CORS.

---

<a id="structure"></a>

## 📁 Project Structure

```text
AWS-Document-Approval-System-Project/
│
├── README.md
├── STEPS.md
├── CONCEPTS.md
│
├── screenshots/
│   ├── architecture-diagram.png
│   ├── 01-dynamodb.png
│   ├── 02-sns-topic.png
│   ├── 03-iam-role.png
│   ├── 04-lambda-submit-config.png
│   ├── 05-lambda-decision-config.png
│   ├── 06-apigateway-invoke.png
│   ├── 08-s3-bucket.png
│   ├── 09-cloudfront-distribution.png
│   ├── 09-s3-bucket-policy.png
│   ├── 11-lambda-env-updated.png
│   ├── 12-fulltest-submit.png
│   ├── 12-fulltest-approval-email.png
│   ├── 12-fulltest-decision-page.png
│   └── 12-fulltest-dynamodb-status.png
│
├── code/
│   ├── frontend/
│   │   └── index.html
│   │
│   └── lambda/
│       ├── submit_handler.py
│       └── decision_handler.py
│
└── iam/
    └── document-approval-lambda-policy.json
```

> Keep the screenshot names synchronized with the actual files in the repository.

---

<a id="test"></a>

## ✅ End-to-End Test

The final test should prove the complete workflow.

| Test | Expected result |
|---|---|
| Open CloudFront URL | Frontend loads |
| Submit PDF | Submission succeeds |
| DynamoDB | Record created with `PENDING` |
| Approver email | Approval links received |
| Click Approve | Confirmation HTML page |
| DynamoDB | Status becomes `APPROVED` |
| Result notification | Notification sent |

For rejection:

```text
PENDING → REJECTED
```

### Test screenshots

- [`12-fulltest-submit.png`](screenshots/12-fulltest-submit.png)
- [`12-fulltest-approval-email.png`](screenshots/12-fulltest-approval-email.png)
- [`12-fulltest-decision-page.png`](screenshots/12-fulltest-decision-page.png)
- [`12-fulltest-dynamodb-status.png`](screenshots/12-fulltest-dynamodb-status.png)

---

<a id="documentation"></a>

## 📚 Project Documentation

### 🛠 Build Log

[`STEPS.md`](STEPS.md)

Contains the deployment steps in the same order the architecture was built.

### 🧠 Design Concepts

[`CONCEPTS.md`](CONCEPTS.md)

Explains the architectural decisions and the questions an instructor/interviewer may ask.

### 🖼 Architecture

[`screenshots/architecture-diagram.png`](screenshots/architecture-diagram.png)

---

<a id="improvements"></a>

## 🚀 Possible Improvements

- Amazon Cognito for authenticated approvers
- Token expiration
- Conditional/atomic DynamoDB status updates
- API Gateway throttling
- AWS WAF for public deployments
- CloudWatch dashboards and alarms
- Terraform or CloudFormation
- Separate SNS notification topics for different recipients

---

<a id="cost"></a>

## 💰 Cost Management

The architecture is serverless and does not use:

```text
EC2
ALB
RDS
```

There is therefore no continuously running EC2/server/database instance.

However:

> **Serverless does not automatically mean zero cost.**

AWS charges can still depend on requests, storage, data transfer, CloudFront usage, and the account's current Free Tier eligibility.

For a small personal development/test workload, usage is expected to be very low.

Before leaving a project running for a long period, check **AWS Billing / Cost Explorer**.

---

<div align="center">

[⬆️ Back to top](#top)

</div>
