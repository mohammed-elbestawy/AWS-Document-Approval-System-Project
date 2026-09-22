<div align="center">

# 📄 AWS Serverless Document Approval System

A serverless workflow where a submitted PDF gets approved or rejected through a secure, one-click email link — no login required for the approver, and no manual tracking of who approved what.

![AWS](https://img.shields.io/badge/AWS-Serverless-FF9900?style=flat-square&logo=amazonaws&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![Status](https://img.shields.io/badge/Status-Complete-2EA44F?style=flat-square)
![Region](https://img.shields.io/badge/Region-eu--north--1-232F3E?style=flat-square)

</div>

---

### Contents
- 🎯 [The Problem](#problem)
- 🏗️ [Architecture](#architecture)
- 🔐 [Security Decisions](#security)
- 🧠 [Skills Demonstrated](#skills)
- ✅ [End-to-End Test](#test)
- 💰 [Cost](#cost)
- 🚀 [Possible Improvements](#improvements)
- 📚 [Documentation](#docs)
- 📁 [Repository Structure](#structure)

---

<a id="problem"></a>
## 🎯 The Problem

Document approval usually means emailing a PDF, chasing the approver over chat or a call, and tracking status from memory or a spreadsheet. There's no single source of truth for where a document stands, and once the file is sent, anyone holding a copy of the link could act on it.

| Risk / Inefficiency | How this project handles it |
|---|---|
| No single source of truth for approval status | DynamoDB holds one authoritative state per document: `PENDING → APPROVED / REJECTED` |
| Chasing approvers manually | SNS emails the approver directly with one-click decision links — no dashboard login needed |
| A stale or resent link could still "work" | Each decision link carries a per-document token the backend validates before acting |
| A document could be approved twice (double-click, reused old email) | `decision-handler` checks the document is still `PENDING` before applying any new decision |

---

<a id="architecture"></a>
## 🏗️ Architecture

<div align="center">

![AWS Document Approval System Architecture](screenshots/architecture-diagram.png)

</div>

```
User
  ↓
CloudFront + OAC
  ↓
Private S3 (Frontend)
  ↓
API Gateway
  ↓
submit-handler
  ├── S3 (PDF)
  ├── DynamoDB (PENDING)
  └── SNS → Approver Email
                ↓
          Approve / Reject
                ↓
          GET /decision
                ↓
        decision-handler
          └── DynamoDB
```

<div align="center">

| Service | Role |
|:---|:---|
| **Amazon S3** | Stores the static frontend and uploaded PDF documents |
| **Amazon CloudFront** | Delivers the frontend over HTTPS |
| **Origin Access Control (OAC)** | Lets CloudFront read the private frontend bucket without making it public |
| **API Gateway** | Exposes `POST /submit` and `GET /decision` |
| **AWS Lambda** | Runs the submission and decision logic |
| **Amazon DynamoDB** | Stores document metadata, token, and approval status |
| **Amazon SNS** | Sends email notifications |
| **AWS IAM** | Scopes each Lambda's permissions to what it actually needs |

</div>

No EC2 or application server involved.

---

<a id="security"></a>
## 🔐 Security Decisions

- **Private S3 + CloudFront/OAC** — the frontend bucket is never public; CloudFront is the only path in, so there's no direct-S3-URL exposure.
- **Per-document token** — authorizes one specific decision without requiring the approver to log in.
  > Deliberately scoped: it proves *"this token matches this document,"* not *"who this person is."* A production version would add authenticated approvers and token expiration — see [Possible Improvements](#improvements).
- **CORS restricted to the real CloudFront domain** instead of `*`, so only the actual frontend can call the API from a browser.
- **State check before transition** — `decision-handler` refuses to act on a document that isn't still `PENDING`, which blocks a stale or reused email link from re-triggering a decision.

---

<a id="skills"></a>
## 🧠 Skills Demonstrated

- Splitting submission and decision logic into two independent Lambda functions, so the two halves of the workflow don't share failure modes
- Enforcing idempotent state transitions server-side instead of trusting the frontend or the email link
- Choosing OAC over public S3 hosting to keep the frontend bucket private end-to-end
- Being explicit about what a lightweight token *doesn't* provide (real authentication) rather than presenting it as a complete security model

---

<a id="test"></a>
## ✅ End-to-End Test

The full workflow was tested from submission through the approval decision and DynamoDB status update.

<div align="center">

| Step | Result |
|:---:|:---:|
| **1. Submit** | ![Submit](screenshots/12-fulltest-submit.png) |
| **2. Approval Email** | ![Approval Email](screenshots/12-fulltest-approval-email.png) |
| **3. Decision Page** | ![Decision Page](screenshots/12-fulltest-decision-page.png) |
| **4. DynamoDB Status** | ![DynamoDB Status](screenshots/12-fulltest-dynamodb-status.png) |
| **5. S3 Storage** | ![S3](screenshots/12-fulltest-S3.png) |

</div>

State path confirmed: `PENDING → APPROVED` or `PENDING → REJECTED`.

---

<a id="cost"></a>
## 💰 Cost

No component here bills by the hour, so nothing needs to be torn down between demos:

| Service | Why it's near-zero cost here |
|:---|:---|
| S3 / CloudFront | Storage and requests fall well inside the always-free tiers at this volume |
| API Gateway / Lambda | Free tier covers 1M+ requests/month; a demo workload uses a fraction of that |
| DynamoDB (on-demand) | Pay-per-request with no idle cost, unlike a provisioned database |
| SNS | Free tier covers far more than the email volume this project generates |

---

<a id="improvements"></a>
## 🚀 Possible Improvements

- Replace the per-document token with authenticated approver identity (real login instead of a link-based token)
- Add token expiration and one-time-use enforcement to remove the replay risk of an old email
- Log who approved/rejected and when, not just the current state
- Move to Infrastructure as Code (Terraform) for repeatable deployment

---

<a id="docs"></a>
## 📚 Documentation

- **[STEPS.md](STEPS.md)** — full build log with configuration screenshots
- **[CONCEPTS.md](CONCEPTS.md)** — extended design rationale for each decision above

---

<a id="structure"></a>
## 📁 Repository Structure

```
AWS-Document-Approval-System-Project/
│
├── README.md
├── STEPS.md
├── CONCEPTS.md
├── screenshots/
├── code/
│   ├── frontend/
│   └── lambda/
└── iam/
```
