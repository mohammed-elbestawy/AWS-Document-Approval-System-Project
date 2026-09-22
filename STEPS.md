<div align="center">

# 🛠️ Build Log — AWS Serverless Document Approval System

A record of the resources created and the configuration used to build the document approval workflow.

![AWS](https://img.shields.io/badge/AWS-Serverless-FF9900?style=flat-square&logo=amazonaws&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![Region](https://img.shields.io/badge/Region-eu--north--1-232F3E?style=flat-square)

</div>

---

### Contents
- 🗃️ [DynamoDB — Approval State](#dynamodb)
- 📣 [SNS — Approval Notifications](#sns)
- 🔐 [IAM — Lambda Execution Role](#iam)
- 🪣 [S3 — Document Storage](#s3-storage)
- ⚡ [Lambda — submit-handler](#submit-handler)
- ⚡ [Lambda — decision-handler](#decision-handler)
- 🔌 [API Gateway](#api-gateway)
- 🌐 [Frontend — S3 Bucket](#frontend-bucket)
- 🌍 [CloudFront + OAC](#cloudfront)
- 📤 [Frontend Upload](#frontend-upload)
- 🔧 [Environment Variables + CORS](#env-vars)
- ✅ [End-to-End Test](#e2e-test)

---

<a id="dynamodb"></a>
## 🗃️ DynamoDB — Approval State

The single table every other function reads and writes to track where a document stands.

| Field | Value |
|:---|:---|
| Table | `document-approvals` |
| Partition key | `doc_id` (String) |
| Capacity mode | On-demand |
| Initial state | `PENDING` |

![DynamoDB configuration](screenshots/01-dynamodb.png)

---

<a id="sns"></a>
## 📣 SNS — Approval Notifications

Delivers the approve/reject links to the person who needs to act, without building a notification system from scratch.

| Field | Value |
|:---|:---|
| Topic | `approval-notifications` |
| Type | Standard |
| Protocol | Email |

> The email subscription must be confirmed before notifications will actually deliver.

![SNS topic configuration](screenshots/02-sns-topic.png)

---

<a id="iam"></a>
## 🔐 IAM — Lambda Execution Role

One role covering exactly what the two Lambda functions touch — nothing broader.

Scoped access to: `CloudWatch Logs` · `S3` · `DynamoDB` · `SNS`

Permissions are limited to the specific resources and actions each function needs — not blanket service-level access.

![IAM role configuration](screenshots/03-iam-role.png)

---

<a id="s3-storage"></a>
## 🪣 S3 — Document Storage

Holds the uploaded PDFs. Never exposed directly — everything reads through the app layer, not the bucket.

Private bucket, not publicly readable at any point in the flow.

![S3 storage configuration](screenshots/04-s3-storage.png)

---

<a id="submit-handler"></a>
## ⚡ Lambda — submit-handler

Handles the incoming submission end to end: validating it, storing it, and notifying the approver.

| Field | Value |
|:---|:---|
| Function | `submit-handler` |
| Runtime | Python 3.12 |

```
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

**Environment variables:** `TABLE_NAME` · `TOPIC_ARN` · `APP_BASE_URL` · `ALLOWED_ORIGIN`

![submit-handler configuration](screenshots/05-lambda-submit-config.png)

---

<a id="decision-handler"></a>
## ⚡ Lambda — decision-handler

Processes the Approve/Reject click — the only function allowed to change a document's state.

| Field | Value |
|:---|:---|
| Function | `decision-handler` |
| Runtime | Python 3.12 |
| Request fields | `doc_id`, `token`, `action` |
| Allowed actions | `approve`, `reject` |

Validates the document, token, action, and current state before updating DynamoDB.

![decision-handler configuration](screenshots/06-lambda-decision-config.png)

---

<a id="api-gateway"></a>
## 🔌 API Gateway

The HTTP front door — two routes, each mapped to one Lambda.

| Route | Purpose |
|:---|:---|
| `POST /submit` | Frontend submits a new document |
| `GET /decision` | Approve/Reject links resolve the decision |

The API Gateway Invoke URL is used as the base URL for the approval links.

![API Gateway configuration](screenshots/07-apigateway-invoke.png)

---

<a id="frontend-bucket"></a>
## 🌐 Frontend — S3 Bucket

Hosts the static site files that CloudFront serves.

Static files (`index.html`, `style.css`, `script.js`) sit in a private bucket. CloudFront is the only public entry point.

---

<a id="cloudfront"></a>
## 🌍 CloudFront + OAC

The public entry point for the frontend, configured so the S3 bucket behind it never has to be public.

| Setting | Value |
|:---|:---|
| Origin type | Amazon S3 — frontend bucket |
| Private S3 access | Enabled via Origin Access Control (OAC) |
| Origin settings | Recommended defaults |
| Cache settings | Recommended (S3 content) |
| Viewer protocol policy | Redirect HTTP → HTTPS |
| Default root object | `index.html` |

![CloudFront distribution](screenshots/09-cloudfront-distribution.png)

CloudFront/OAC is the trusted path for reading the private frontend bucket — the S3 bucket policy reflects that.

![S3 bucket policy](screenshots/09-s3-bucket-policy.png)

---

<a id="frontend-upload"></a>
## 📤 Frontend Upload

Gets the built frontend live once the bucket and distribution exist.

Frontend files uploaded to the bucket. The bucket is never made public to serve the site — CloudFront + OAC stays the only access path.

---

<a id="env-vars"></a>
## 🔧 Environment Variables + CORS

Wires the deployed URLs back into the Lambda functions once they're known.

| Variable | Value | Why |
|:---|:---|:---|
| `APP_BASE_URL` | API Gateway Invoke URL | Approval links point to `/decision` on this API |
| `ALLOWED_ORIGIN` | CloudFront domain | Represents the actual browser origin allowed to call the API |

![Final Lambda environment variables](screenshots/11-lambda-env-updated.png)

---

<a id="e2e-test"></a>
## ✅ End-to-End Test

Confirms the whole chain — submission to decision to stored state — actually works together.

<div align="center">

| Check | Result |
|:---:|:---:|
| Submit | ![Submit](screenshots/12-fulltest-submit.png) |
| Approval email | ![Approval email](screenshots/12-fulltest-approval-email.png) |
| Decision page | ![Decision page](screenshots/12-fulltest-decision-page.png) |
| DynamoDB status | ![DynamoDB status](screenshots/12-fulltest-dynamodb-status.png) |
| S3 | ![S3](screenshots/12-fulltest-S3.png) |

</div>

State path confirmed: `PENDING → APPROVED` or `PENDING → REJECTED`.
