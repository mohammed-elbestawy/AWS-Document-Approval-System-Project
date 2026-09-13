<a id="top"></a>

# 🧠 Design Concepts & Rationale

> The main architecture and security concepts to understand before presenting the project to an instructor.

## 📋 Quick Navigation

- [Architecture](#architecture)
- [S3 + CloudFront + OAC](#oac)
- [Serverless](#serverless)
- [API Gateway](#api)
- [DynamoDB](#dynamodb)
- [SNS](#sns)
- [Approval Token](#token)
- [CORS](#cors)
- [IAM](#iam)
- [State Management](#state)
- [Cost](#cost)
- [Presentation](#presentation)

<a id="architecture"></a>

## 🏗 Architecture

![Architecture Diagram](screenshots/architecture-diagram.png)

The architecture has four main stages:

```text
1. Frontend delivery
2. Document submission
3. Approval decision
4. State + notification
```

The frontend is delivered by CloudFront from a private S3 bucket. API Gateway exposes the backend endpoints. Lambda performs the application logic, DynamoDB stores the workflow state, and SNS sends email notifications.

<a id="oac"></a>

## 🌍 Why S3 + CloudFront + OAC?

The frontend is static, so S3 is suitable for storage and CloudFront provides the public HTTPS delivery layer.

The important security decision is **Origin Access Control (OAC)**.

```text
Internet
   ↓
CloudFront
   ↓
OAC
   ↓
Private S3
```

This avoids making the frontend bucket publicly readable.

### Why not public S3?

A public bucket allows users to access objects directly through S3. With OAC, CloudFront is the intended public entry point while the S3 bucket remains private.

<a id="serverless"></a>

## ⚡ Why Serverless?

The application does not require a continuously running server.

Instead:

```text
API Request
    ↓
Lambda
    ↓
AWS managed services
```

There is no EC2 instance, web server or load balancer to manage.

### Why two Lambda functions?

| Function | Responsibility |
|---|---|
| `submit-handler` | Handles document submission and creates the approval request |
| `decision-handler` | Handles Approve / Reject decisions |

Separating the responsibilities makes the workflow easier to understand and maintain.

<a id="api"></a>

## 🔌 Why API Gateway?

API Gateway provides the HTTP interface between the frontend/approval links and Lambda.

```text
POST /submit
GET  /decision
```

The `/decision` endpoint is a GET because the approver receives a normal hyperlink in an email.

<a id="dynamodb"></a>

## 🗃 Why DynamoDB?

The application needs to find a document by ID, validate its token, read its current status and update that status.

DynamoDB fits this simple key-value/document access pattern.

### Main state

```text
PENDING
APPROVED
REJECTED
```

On-Demand capacity is suitable for a low and unpredictable learning/demo workload because capacity does not need to be planned in advance.

<a id="sns"></a>

## 📣 Why SNS?

SNS provides managed notifications without running an email server.

```text
Lambda
   ↓
SNS Topic
   ↓
Email Subscription
```

It is used for the approval notification and the configured result notification flow.

<a id="token"></a>

## 🔑 Why an Approval Token?

The approval URL contains both a document ID and a per-document token.

```text
doc_id + token + action
            ↓
     decision-handler
            ↓
        DynamoDB
```

The Lambda checks that the supplied token belongs to the requested document before processing the decision.

### Important limitation

A token in a URL is **not the same as user authentication**.

For a larger production system, the approval workflow could be strengthened with Cognito authentication, token expiration, one-time-use tokens and conditional DynamoDB updates.

<a id="cors"></a>

## 🔒 Why Restrict CORS?

The frontend is served from the CloudFront domain, so the API should allow that actual origin rather than using:

```text
*
```

Example:

```text
ALLOWED_ORIGIN=https://<cloudfront-domain>
```

### Interview point

CORS is a **browser security mechanism**. It does not replace backend authorization or token validation.

<a id="iam"></a>

## 🛡 IAM & Least Privilege

Lambda accesses AWS services through an IAM execution role.

The principle is:

```text
Only required actions
+
Only required resources
```

Resource ARNs should be restricted where the AWS service supports resource-level permissions.

Least privilege reduces the possible impact if a function is compromised.

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

The decision Lambda checks that the document is still `PENDING` before changing its state.

A stronger production version can use a conditional/atomic DynamoDB update to prevent race conditions when two decision requests arrive at nearly the same time.

<a id="cost"></a>

## 💰 Cost

Serverless does not mean automatically free.

Potential charges can come from:

- S3 storage and requests
- CloudFront traffic
- API Gateway requests
- Lambda execution
- DynamoDB usage
- SNS usage

For a small learning project the usage can be very low, but AWS Billing should still be monitored.

<a id="presentation"></a>

# 🎤 Instructor Presentation

### One-minute explanation

> **"This is a fully serverless document approval system. The frontend is stored in a private S3 bucket and delivered through CloudFront using Origin Access Control, so the bucket does not need to be public. When the user submits a PDF, the frontend sends the request to API Gateway, which invokes the submit Lambda. The Lambda validates the request, stores the document in S3, creates a PENDING record in DynamoDB, and sends an approval notification through SNS. The approver receives Approve and Reject links. These links call the `/decision` endpoint, which invokes the decision Lambda. It validates the document ID, token, action and current status, then updates DynamoDB to APPROVED or REJECTED and sends the configured result notification. The whole backend is serverless, so there are no EC2 servers to manage."**

### Questions the instructor may ask

**Why CloudFront?**  
To provide HTTPS delivery and allow the S3 frontend bucket to remain private through OAC.

**Why DynamoDB?**  
The application needs simple key-based document lookup and status updates.

**Why SNS?**  
To send email notifications without managing an email server.

**Why two Lambdas?**  
To separate submission logic from approval-decision logic.

**Why CORS restriction?**  
To allow the real frontend origin instead of every browser origin.

**Is the token authentication?**  
No. It is a per-document authorization mechanism. Full user authentication could be added with Cognito.

**What happens to the document state?**

```text
PENDING → APPROVED
       ↘ REJECTED
```

---

<div align="center">

[⬆️ Back to top](#top)

</div>
