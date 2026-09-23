<div align="center">

# 🧠 Design Concepts — AWS Serverless Document Approval System

The architecture, service roles, and security decisions behind the approval workflow, with the reasoning behind each.

![AWS](https://img.shields.io/badge/AWS-Serverless-FF9900?style=flat-square&logo=amazonaws&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![Region](https://img.shields.io/badge/Region-eu--north--1-232F3E?style=flat-square)

</div>

---

### At a Glance

| Decision | Why |
|:---|:---|
| CloudFront + OAC over public S3 | Public HTTPS delivery without ever exposing the bucket |
| Per-document token, not full auth | Lightweight authorization scoped to one decision, not a login system |
| CORS restricted to the real origin | Only the actual frontend can call the API from a browser |
| State check before transition | Blocks a stale or reused email link from re-triggering a decision |
| No EC2 | Fully managed compute via Lambda — no server to patch or run |

### Contents

[![Architecture](https://img.shields.io/badge/Architecture-30363D?style=flat-square)](#architecture)
[![Frontend Delivery](https://img.shields.io/badge/Frontend_Delivery-30363D?style=flat-square)](#frontend-delivery)
[![Submission Flow](https://img.shields.io/badge/Submission_Flow-30363D?style=flat-square)](#submission-flow)
[![Approval Flow](https://img.shields.io/badge/Approval_Flow-30363D?style=flat-square)](#approval-flow)
[![DynamoDB State](https://img.shields.io/badge/DynamoDB_State-30363D?style=flat-square)](#dynamodb-state)
[![SNS Notifications](https://img.shields.io/badge/SNS_Notifications-30363D?style=flat-square)](#sns-notifications)
[![Serverless Design](https://img.shields.io/badge/Serverless_Design-30363D?style=flat-square)](#serverless-design)
[![API Gateway](https://img.shields.io/badge/API_Gateway-30363D?style=flat-square)](#api-gateway)
[![Approval Token](https://img.shields.io/badge/Approval_Token-30363D?style=flat-square)](#approval-token)
[![Security Decisions](https://img.shields.io/badge/Security_Decisions-30363D?style=flat-square)](#security-decisions)
[![IAM](https://img.shields.io/badge/IAM-30363D?style=flat-square)](#iam)
[![Cost](https://img.shields.io/badge/Cost-30363D?style=flat-square)](#cost)

---

<a id="architecture"></a>
## 🏗️ Architecture

![Architecture Diagram](screenshots/architecture-diagram.png)

Each AWS service in this project has one clear responsibility.

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

The document starts in `PENDING` and moves to `APPROVED` or `REJECTED`.

---

<a id="frontend-delivery"></a>
## 🌍 Frontend Delivery — S3 + CloudFront + OAC

```
Internet → CloudFront → Origin Access Control (OAC) → Private S3 Bucket
```

| Question | Answer |
|:---|:---|
| Why CloudFront? | Public HTTPS delivery layer, with caching for static files close to users |
| Why OAC? | Lets CloudFront read the private bucket without making it publicly readable — the path stays `User → CloudFront → S3`, never direct public access |
| Why not S3 static website hosting? | The project uses the S3 REST origin with CloudFront/OAC, which doesn't require static website hosting for a private-bucket design |

---

<a id="submission-flow"></a>
## 📤 Document Submission Flow

```
Frontend → POST /submit → API Gateway → submit-handler
                                              │
                          ┌───────────────────┼───────────────────┐
                          ▼                   ▼                   ▼
                       S3 (PDF)         DynamoDB (PENDING)   SNS → Approval Email
```

`submit-handler` owns the submission logic end to end: storing the document, creating the approval record, and firing the notification.

---

<a id="approval-flow"></a>
## ✅ Approval / Rejection Flow

```
Approver → Approve/Reject link → API Gateway → decision-handler
                                                      │
                                    Validate request → Check token + status
                                                      │
                                          Update DynamoDB → APPROVED / REJECTED
```

Keeping `submit-handler` and `decision-handler` as separate functions means the two halves of the workflow don't share a failure mode.

---

<a id="dynamodb-state"></a>
## 🗃️ DynamoDB — Workflow State

The identifier is `doc_id`; the state is one of `PENDING`, `APPROVED`, `REJECTED`.

```
             ┌───────────┐
             │  PENDING  │
             └─────┬─────┘
                   │
            ┌──────┴──────┐
         Approve        Reject
            │             │
            ▼             ▼
       ┌──────────┐  ┌──────────┐
       │ APPROVED │  │ REJECTED │
       └──────────┘  └──────────┘
```

`decision-handler` checks the current state before changing it — this stops a document that's no longer pending from being treated as a fresh decision.

---

<a id="sns-notifications"></a>
## 📣 SNS — Email Notifications

```
Lambda → SNS Topic → Email Subscription → Approver
```

A managed notification layer means the project never has to run or maintain its own mail infrastructure.

---

<a id="serverless-design"></a>
## ⚡ Serverless Design

No EC2, application server, or load balancer anywhere in the stack.

```
API Gateway → Lambda → S3 / DynamoDB / SNS
```

Lambda runs the logic on demand; S3, DynamoDB, and SNS handle storage and notifications as managed services — no OS to patch, no server to keep alive.

---

<a id="api-gateway"></a>
## 🔌 API Gateway

| Route | Used by |
|:---|:---|
| `POST /submit` | The frontend, to submit a document |
| `GET /decision` | The Approve/Reject links sent by email |

API Gateway keeps the frontend decoupled from the Lambda implementation and gives the project a clear API boundary.

---

<a id="approval-token"></a>
## 🔑 Approval Token

```
doc_id + token + action → decision-handler → DynamoDB
```

`decision-handler` verifies the token matches the requested document before acting on it.

> **Important distinction:** the approval token is not a full user-authentication system — it authorizes *this specific document decision*, not *this specific person*. A production version would add authenticated approvers, token expiration, and one-time-use tokens.

---

<a id="security-decisions"></a>
## 🔒 Security Decisions

| Control | What it does |
|:---|:---|
| Private S3 bucket | Not publicly readable; CloudFront/OAC is the only access path |
| HTTPS everywhere | CloudFront redirects HTTP requests to HTTPS |
| Restricted CORS | Frontend origin set to the real CloudFront domain instead of `*` — CORS controls browser origins, it doesn't replace backend authorization |
| Input validation | Lambda functions validate incoming data before processing it |
| Approval state validation | `decision-handler` checks the current DynamoDB status before applying a new decision |

---

<a id="iam"></a>
## 🛡️ IAM — Least Privilege

```
Required actions + Required resources = Least privilege
```

Each Lambda's permissions are limited to what it actually needs — its own S3 bucket, DynamoDB table, SNS topic, and CloudWatch Logs. This keeps the blast radius small if a function or its credentials are ever misused.

---

<a id="cost"></a>
## 💰 Cost Considerations

Serverless doesn't mean every resource is permanently free. Usage-based charges can come from S3 storage/requests, CloudFront transfer, API Gateway requests, Lambda execution, DynamoDB usage, and SNS usage.

For a small learning project the workload stays very low — but billing is still worth monitoring.
