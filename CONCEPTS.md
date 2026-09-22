# 🧠 Design Concepts — AWS Serverless Document Approval System

A clean explanation of the architecture, AWS services, security decisions, and approval workflow used in the project.

### Contents
- [Architecture](#architecture)
- [Frontend Delivery](#frontend-delivery--s3--cloudfront--oac)
- [Document Submission Flow](#document-submission-flow)
- [Approval / Rejection Flow](#approval--rejection-flow)
- [DynamoDB — Workflow State](#dynamodb--workflow-state)
- [SNS — Email Notifications](#sns--email-notifications)
- [Serverless Design](#serverless-design)
- [API Gateway](#api-gateway)
- [Approval Token](#approval-token)
- [Security Decisions](#security-decisions)
- [IAM — Least Privilege](#iam--least-privilege)
- [Cost Considerations](#cost-considerations)

---

## Architecture

![Architecture Diagram](screenshots/architecture-diagram.png)

The project is built as a serverless approval workflow. Each AWS service has one clear responsibility.

```
User
  ↓
CloudFront + OAC
  ↓
Private S3
  ↓
API Gateway
  ↓
submit-handler
  ├── S3
  ├── DynamoDB
  └── SNS
       ↓
  Approver Email
       ↓
 Approve / Reject
       ↓
 GET /decision
       ↓
 decision-handler
       ↓
 DynamoDB
```

The document starts in `PENDING` and can then move to `APPROVED` or `REJECTED`.

---

## Frontend Delivery — S3 + CloudFront + OAC

The frontend is a static website, so its files live in Amazon S3. The S3 frontend bucket stays private; CloudFront is the public delivery layer.

```
Internet
   ↓
CloudFront
   ↓
Origin Access Control (OAC)
   ↓
Private S3 Bucket
```

**Why CloudFront?** It provides the public HTTPS delivery layer for the frontend and can cache static files close to users.

**Why OAC?** It lets CloudFront access the private S3 bucket without making the bucket publicly readable — the path is `User → CloudFront → S3`, never direct public access to the S3 objects.

**Why no S3 Static Website Hosting?** The project uses the S3 REST origin with CloudFront/OAC, so static website hosting isn't required for a private-bucket design.

---

## Document Submission Flow

```
Frontend
   ↓
POST /submit
   ↓
API Gateway
   ↓
submit-handler
   ↓
┌───────────────┬────────────────┬────────────────┐
│               │                │                │
▼               ▼                ▼                ▼
S3           DynamoDB          SNS          Approval Email
PDF           PENDING        Notification       │
                                                 │
                                                 ▼
                                         Approve / Reject
```

`submit-handler` owns the submission logic: it stores the document, creates the approval record, and sends the notification.

---

## Approval / Rejection Flow

The approver receives links for both possible decisions. The links reach `GET /decision` with the document ID, token, and requested action, processed by `decision-handler`.

```
Approver
   ↓
Approve / Reject link
   ↓
API Gateway
   ↓
decision-handler
   ↓
Validate request
   ↓
Check token + current status
   ↓
Update DynamoDB
   ↓
APPROVED / REJECTED
```

Keeping `submit-handler` and `decision-handler` separate means the two halves of the workflow don't share a failure mode.

---

## DynamoDB — Workflow State

The main identifier is `doc_id`. The approval state is one of `PENDING`, `APPROVED`, `REJECTED`.

```
             ┌───────────┐
             │  PENDING  │
             └─────┬─────┘
                   │
            ┌──────┴──────┐
            │             │
         Approve        Reject
            │             │
            ▼             ▼
       ┌──────────┐  ┌──────────┐
       │ APPROVED │  │ REJECTED │
       └──────────┘  └──────────┘
```

`decision-handler` checks the current state before changing it — this stops a document that's no longer pending from being treated as a new approval decision.

---

## SNS — Email Notifications

```
Lambda
   ↓
SNS Topic
   ↓
Email Subscription
   ↓
Approver
```

Using a managed notification layer means the project doesn't need to run or manage its own email server.

---

## Serverless Design

No EC2, application server, or load balancer.

```
API Gateway
     ↓
   Lambda
     ↓
S3 / DynamoDB / SNS
```

**Benefits here:** no server administration, no OS maintenance — Lambda runs the logic on demand, while S3, DynamoDB, and SNS provide managed storage and notifications.

---

## API Gateway

Two routes:
- **`POST /submit`** — used by the frontend to submit the document
- **`GET /decision`** — used by the Approve/Reject links sent in the email

API Gateway keeps the frontend separate from the Lambda implementation and gives the project a clear API layer.

---

## Approval Token

```
doc_id + token + action
          ↓
   decision-handler
          ↓
       DynamoDB
```

`decision-handler` verifies the token matches the requested document before processing the action.

> **Important distinction:** the approval token is not a full user-authentication system — it authorizes *this specific document decision*, not *this specific person*. A production version would add authenticated approvers, token expiration, and one-time-use tokens.

---

## Security Decisions

- **Private S3 bucket** — the frontend bucket isn't publicly readable; CloudFront/OAC is the access path.
- **HTTPS** — CloudFront redirects HTTP requests to HTTPS.
- **Restricted CORS** — the frontend origin is set to the real CloudFront domain instead of `*`. CORS controls which browser origins can make cross-origin requests; it doesn't replace backend authorization.
- **Input validation** — the Lambda functions validate incoming data before processing it.
- **Approval state validation** — `decision-handler` checks the current DynamoDB status before applying a new decision.

---

## IAM — Least Privilege

Lambda accesses AWS resources through IAM execution roles, scoped to:

```
Required actions + Required resources = Least privilege
```

Permissions are limited to what each Lambda actually needs — the relevant S3 bucket, DynamoDB table, SNS topic, and CloudWatch Logs. This reduces the blast radius if a function or its credentials are ever misused.

---

## Cost Considerations

Serverless doesn't mean every resource is permanently free. Usage-based charges can come from:

- S3 storage and requests
- CloudFront data transfer and requests
- API Gateway requests
- Lambda execution
- DynamoDB usage
- SNS usage

For a small learning project, the workload stays very low — but billing should still be monitored.
