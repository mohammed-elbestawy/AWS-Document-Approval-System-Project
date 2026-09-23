<div align="center">

# 🧠 Design Concepts & Rationale

This file explains **why** each decision was made — the questions most likely to come up in an interview.

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

[![Architecture & Flow](https://img.shields.io/badge/Architecture_%26_Flow-30363D?style=flat-square)](#architecture)
[![Workflow State](https://img.shields.io/badge/Workflow_State-30363D?style=flat-square)](#state)
[![Notifications](https://img.shields.io/badge/Notifications-30363D?style=flat-square)](#notifications)
[![API & Authorization](https://img.shields.io/badge/API_%26_Authorization-30363D?style=flat-square)](#api)
[![Security](https://img.shields.io/badge/Security-30363D?style=flat-square)](#security)
[![Cost](https://img.shields.io/badge/Cost-30363D?style=flat-square)](#cost)

---

<a id="architecture"></a>
## 🏗️ Architecture & Flow

![Architecture Diagram](screenshots/architecture-diagram.png)

```
User → CloudFront + OAC → Private S3 → API Gateway → submit-handler
                                                          ├── S3 (PDF)
                                                          ├── DynamoDB (PENDING)
                                                          └── SNS → Approver Email
                                                                        ↓
                                                              GET /decision → decision-handler → DynamoDB
```

| Question | Answer |
|:---|:---|
| Why split submission and decision handling into two separate Lambda functions instead of one? | They're two independent lifecycles triggered by different actors at different times — the submitter and the approver never interact with the same code path. Keeping them separate means a change to one can't break the other. |
| Why CloudFront + OAC instead of a public bucket or S3 static website hosting? | OAC lets CloudFront read the private bucket without ever exposing it directly, and it keeps delivery on HTTPS with caching. Static website hosting doesn't support that private-bucket path the same way. |
| Why no EC2 or application server anywhere in the stack? | The workflow is bursty and infrequent — API Gateway and Lambda handle that pattern for free at low volume, with no server to patch or keep running between submissions. |

---

<a id="state"></a>
## 🗃️ Workflow State

| Question | Answer |
|:---|:---|
| Why does the state live in DynamoDB instead of being tracked through the email thread itself? | An email thread isn't queryable or enforceable — anyone could reply out of order or twice. DynamoDB gives one authoritative state (`PENDING → APPROVED/REJECTED`) the backend can actually check before acting. |
| Why does `decision-handler` check the current state before applying a new decision? | Without that check, a stale or resent email link could re-trigger a decision on a document that's already resolved. The check makes the transition idempotent instead of repeatable. |

---

<a id="notifications"></a>
## 📣 Notifications

| Question | Answer |
|:---|:---|
| Why SNS instead of sending email directly from the Lambda function? | SNS is a managed notification layer — no mail server, no handling retries or delivery failures by hand. The Lambda's only job is to publish; SNS owns delivery. |

---

<a id="api"></a>
## 🔌 API & Authorization

| Question | Answer |
|:---|:---|
| Why a per-document token instead of just the document ID in the link? | A bare document ID is guessable or enumerable. The token means only someone who actually received the email can act on that specific document. |
| Is the token a substitute for real authentication? | No — deliberately not. It proves *"this token matches this document,"* not *"who this person is."* A production version would add authenticated approvers, token expiration, and one-time-use tokens. |
| Why two separate routes (`POST /submit`, `GET /decision`) instead of one generic endpoint? | Submission and decision have completely different payloads, callers, and security needs — separate routes keep each Lambda's input validation simple and specific to its job. |

---

<a id="security"></a>
## 🔒 Security

| Question | Answer |
|:---|:---|
| Why restrict CORS to the real CloudFront domain instead of `*`? | CORS controls which browser origins can call the API — it doesn't replace backend authorization, but scoping it to the real frontend still closes an easy, free-to-fix gap. |
| Why does the IAM role avoid wildcard resource ARNs? | Least privilege — each Lambda only ever touches its own S3 bucket, DynamoDB table, and SNS topic. A wildcard would grant access to anything created later in the account, a bigger blast radius than the app needs. |

---

<a id="cost"></a>
## 💰 Cost

| Question | Answer |
|:---|:---|
| Why doesn't this project need the same teardown discipline as projects using EC2 or ALB? | Every service here — S3, CloudFront, API Gateway, Lambda, DynamoDB, SNS — has an always-free tier or near-zero idle cost. Nothing bills by the hour regardless of traffic. |
| Why On-Demand DynamoDB instead of provisioned capacity? | Approval volume is low and unpredictable at this scale — On-Demand avoids both throttling risk and paying for capacity that may sit idle. |
