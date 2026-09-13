<a id="top"></a>

# 🧠 Design Concepts & Rationale — AWS Document Approval System

> The questions below are the most important concepts to understand before presenting the architecture to an instructor or interviewer.

## 📋 Quick Navigation

| Topic | Section |
|---|---|
| 🌍 | [Frontend Delivery](#frontend) |
| 🪣 | [S3 & OAC](#s3) |
| ⚡ | [Serverless Architecture](#serverless) |
| 🔌 | [API Gateway](#api) |
| 🗃 | [DynamoDB](#dynamodb) |
| 📣 | [SNS](#sns) |
| 🔑 | [Approval Security](#approval) |
| 🔒 | [CORS](#cors) |
| 🛡 | [IAM](#iam) |
| 🔄 | [State Management](#state) |
| 💰 | [Cost](#cost) |
| 🚀 | [Future Improvements](#improvements) |

---

<a id="frontend"></a>

## 🌍 Frontend Delivery

### Why S3 + CloudFront?

The frontend consists of static files, so it does not require a continuously running web server.

```text
CloudFront
    ↓
Private S3
```

CloudFront provides the public HTTPS delivery layer while S3 stores the static files.

### Why not use S3 Website Hosting?

With the private-bucket design, the project does not need S3 Website Hosting.

CloudFront reads the bucket through the S3 origin API using OAC.

This allows:

```text
S3 Block Public Access = ON
```

while still serving the website publicly through CloudFront.

---

<a id="s3"></a>

## 🪣 S3 & Origin Access Control

### What is OAC?

**Origin Access Control** allows CloudFront to access an S3 origin while keeping the bucket private.

The security model is:

```text
Internet
   ↓
CloudFront
   ↓
OAC
   ↓
Private S3
```

Instead of:

```text
Internet
   ↓
Public S3 bucket
```

### Why is this better?

A public bucket exposes the S3 objects directly.

With OAC:

- Block Public Access remains enabled.
- CloudFront is the intended public entry point.
- Direct S3 access is not the normal access path.

This reduces the attack surface.

---

<a id="serverless"></a>

## ⚡ Serverless Architecture

### Why serverless?

The workflow is event/request driven.

There is no need for:

```text
EC2
Web Server
Load Balancer
```

The main backend path is:

```text
API Gateway
      ↓
Lambda
      ↓
AWS managed services
```

This reduces infrastructure management.

### Why two Lambda functions?

Responsibilities are separated:

| Lambda | Responsibility |
|---|---|
| `submit-handler` | Creates the document approval request |
| `decision-handler` | Processes Approve / Reject |

This makes the workflow easier to understand and maintain.

---

<a id="api"></a>

## 🔌 API Gateway

### Why API Gateway?

API Gateway provides the HTTP interface between the frontend/email links and Lambda.

The project exposes:

```text
POST /submit
GET /decision
```

This gives the architecture a clear API boundary.

### Why is `/decision` a GET?

The approval link is opened from an email.

A hyperlink can directly open:

```text
GET /decision?doc_id=...&token=...&action=approve
```

The Lambda processes the decision and returns a small HTML result page.

---

<a id="dynamodb"></a>

## 🗃 DynamoDB

### Why DynamoDB?

The workflow needs to:

- identify a document
- retrieve its metadata
- validate its approval token
- read its current status
- update the decision

DynamoDB fits this simple key-value/document access pattern.

### Why On-Demand?

Traffic for a personal approval system is usually low and unpredictable.

On-Demand capacity avoids having to plan provisioned throughput.

### Main state

```text
PENDING
APPROVED
REJECTED
```

---

<a id="sns"></a>

## 📣 SNS

### Why SNS?

The application needs email notifications without managing an email server.

The notification flow is:

```text
Lambda
   ↓
SNS Topic
   ↓
Email Subscription
```

SNS is therefore separated from the Lambda's core document-storage logic.

---

<a id="approval"></a>

## 🔑 Approval Security

### Why use a token?

The approval URL contains a random per-document token.

Conceptually:

```text
Approve URL
    ↓
doc_id + token + action
    ↓
decision-handler
    ↓
DynamoDB
    ↓
Compare token
```

If the token is invalid, the request is rejected.

### Why not Cognito?

The current project is designed around a simple approval workflow with a designated approver.

Cognito would add a complete authentication layer:

```text
Users
Passwords
Authentication
Sessions/tokens
Account management
```

For a small learning project, a per-document approval token keeps the architecture simpler.

For a real multi-user production application, authenticated approvers would be a stronger design.

### Important limitation

A token in a URL is not the same thing as user authentication.

A stronger production implementation could add:

- Cognito
- token expiration
- one-time-use tokens
- conditional DynamoDB updates
- stronger audit logging

---

<a id="cors"></a>

## 🔒 CORS

### Why restrict CORS?

The frontend is served from CloudFront.

The backend therefore allows the actual frontend origin instead of:

```text
*
```

Example:

```text
ALLOWED_ORIGIN =
https://<distribution-id>.cloudfront.net
```

### Important interview point

CORS is a **browser security mechanism**.

It does not replace backend authorization.

The approval token is still checked by the Lambda.

---

<a id="iam"></a>

## 🛡 IAM & Least Privilege

Lambda accesses other AWS services through an IAM execution role.

The goal is:

```text
Only required actions
+
Only required resources
```

For example, DynamoDB access should be scoped to the project table when possible.

If an AWS service/action does not support resource-level restriction, `Resource: "*"` may be required.

### Why is this important?

If a Lambda is compromised, overly broad permissions increase the possible impact.

Least privilege reduces that blast radius.

---

<a id="state"></a>

## 🔄 State Management

The document follows a simple state machine:

```text
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

### Why check `PENDING`?

Without a status check, the same document could potentially be processed repeatedly.

The workflow therefore expects a decision only while the document is still pending.

A stronger production version can make the DynamoDB transition conditional/atomic.

---

<a id="cost"></a>

## 💰 Cost Decisions

### Why no EC2?

The project does not need a continuously running server.

Lambda runs only when invoked.

### Does serverless mean free?

No.

Possible sources of AWS charges include:

- S3 storage
- S3 requests
- CloudFront requests/data transfer
- API Gateway requests
- Lambda execution
- DynamoDB usage
- SNS usage/email
- data transfer

Actual pricing also depends on the current Free Tier and account eligibility.

For a small development/test workload, usage should be very low.

---

<a id="improvements"></a>

## 🚀 Future Improvements

### 1. Amazon Cognito

Add authenticated approver accounts.

### 2. Token expiration

Store an expiration timestamp and reject expired links.

### 3. Atomic status transition

Use a conditional DynamoDB update so only a `PENDING` record can transition to a final state.

### 4. API throttling

Add API Gateway throttling to reduce abuse/spam.

### 5. AWS WAF

For a public production deployment, WAF can add another protection layer.

### 6. Infrastructure as Code

Use Terraform or CloudFormation to make the infrastructure reproducible.

### 7. Monitoring

Add CloudWatch dashboards and alarms for:

```text
Lambda errors
API errors
Unusual traffic
Notification failures
```

---

## 🎤 Presentation Summary

If the instructor asks:

> **"Explain your architecture in one minute."**

Use this:

> "The project is a fully serverless document approval system. The frontend is stored in a private S3 bucket and delivered through CloudFront using Origin Access Control, so the bucket does not need to be public. The frontend sends the document submission to API Gateway, which invokes the submit Lambda. The Lambda validates the request, stores the document in S3, creates a PENDING record in DynamoDB, and sends an approval notification through SNS. The approver receives Approve and Reject links. These links call the `/decision` API endpoint, which invokes a second Lambda. The decision Lambda validates the document ID, approval token, action, and current PENDING status, then changes the record to APPROVED or REJECTED and sends the result notification. The whole backend is serverless, so there are no EC2 servers to manage."

---

<div align="center">

[⬆️ Back to top](#top)

</div>
