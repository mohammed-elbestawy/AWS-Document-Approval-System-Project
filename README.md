<a id="top"></a>

# 📄 AWS Serverless Document Approval System

> A fully serverless AWS workflow for submitting PDF documents, notifying an approver by email, and processing **Approve / Reject** decisions through secure per-document links.

![AWS](https://img.shields.io/badge/AWS-Serverless-FF9900?style=flat&logo=amazonaws&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![Status](https://img.shields.io/badge/Status-Tested-brightgreen)

---

## 📋 Table of Contents

| Section | Description |
|---|---|
| 🎯 [Overview](#overview) | What the project does |
| 🏗 [Architecture](#architecture) | High-level AWS architecture |
| ☁️ [AWS Services](#services) | Services and responsibilities |
| 🔐 [Security](#security) | Main security controls |
| ✅ [End-to-End Test](#test) | Complete test results |
| 📁 [Project Structure](#structure) | Repository organization |
| 📚 [Documentation](#documentation) | STEPS and CONCEPTS |
| 💰 [Cost](#cost) | Cost considerations |

---

<a id="overview"></a>

## 🎯 Overview

This project implements a **serverless document approval workflow on AWS**.

A user opens the frontend through **CloudFront**, submits a PDF, and the request is handled by **API Gateway** and Lambda. The document is stored in S3, its approval state is stored in DynamoDB, and SNS sends the approver an email containing the decision links.

The approver can choose **Approve** or **Reject**. The decision is processed by a separate Lambda function and the document state is updated in DynamoDB.

There is **no EC2 instance or traditional application server**.

---

<a id="architecture"></a>

## 🏗 Architecture

![AWS Document Approval System Architecture](screenshots/architecture-diagram.png)

The main flow is:

```text
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

---

<a id="services"></a>

## ☁️ AWS Services

- **Amazon S3** — stores the static frontend and uploaded PDF documents.
- **Amazon CloudFront** — delivers the frontend over HTTPS.
- **Origin Access Control (OAC)** — allows CloudFront to access the private frontend bucket.
- **API Gateway** — exposes `POST /submit` and `GET /decision`.
- **AWS Lambda** — contains the submission and decision logic.
- **Amazon DynamoDB** — stores document metadata, token and approval status.
- **Amazon SNS** — sends email notifications.
- **AWS IAM** — controls Lambda permissions.

**Deployment region:** `eu-north-1`

---

<a id="security"></a>

## 🔐 Security

- Frontend S3 bucket remains **private**.
- CloudFront uses **Origin Access Control (OAC)** to access the bucket.
- HTTP is redirected to HTTPS through CloudFront.
- CORS is restricted to the actual CloudFront origin.
- Approval requests use a document ID and per-document token.
- The decision flow checks that the document is still `PENDING` before changing its status.
- Lambda functions use IAM execution roles for AWS service access.

---

<a id="test"></a>

## ✅ End-to-End Test

The complete workflow was tested successfully from document submission through the approval decision and DynamoDB status update.

### 1. Submit

![Full Test - Submit](screenshots/12-fulltest-submit.png)

### 2. Approval Email

![Full Test - Approval Email](screenshots/12-fulltest-approval-email.png)

### 3. Decision Page

![Full Test - Decision Page](screenshots/12-fulltest-decision-page.png)

### 4. DynamoDB Status

![Full Test - DynamoDB Status](screenshots/12-fulltest-dynamodb-status.png)

The document state follows:

```text
PENDING → APPROVED
```

or

```text
PENDING → REJECTED
```

---

<a id="structure"></a>

## 📁 Project Structure

```text
AWS-Document-Approval-System-Project/
│
├── README.md
├── STEPS.md
├── CONCEPTS.md
├── screenshots/
│   ├── architecture-diagram.png
│   ├── 01-dynamodb.png
│   ├── 02-sns-topic.png
│   ├── 03-iam-role.png
│   ├── 04-s3-storage.png
│   ├── 05-lambda-submit-config.png
│   ├── 06-lambda-decision-config.png
│   ├── 07-apigateway-invoke.png
│   ├── 09-cloudfront-distribution.png
│   ├── 09-s3-bucket-policy.png
│   ├── 11-lambda-env-updated.png
│   └── 12-fulltest-*.png
│
├── code/
│   ├── frontend/
│   └── lambda/
│
└── iam/
```

---

<a id="documentation"></a>

## 📚 Documentation

- 🛠 **[STEPS.md](STEPS.md)** — complete build and configuration steps with the project screenshots.
- 🧠 **[CONCEPTS.md](CONCEPTS.md)** — architecture, AWS service roles, security decisions and workflow concepts.

---

<a id="cost"></a>

## 💰 Cost

The architecture is serverless, but **serverless does not automatically mean free**. AWS charges can depend on storage, requests, traffic and execution across the services used.

For a small learning/demo workload, usage is expected to be low. AWS Billing should still be monitored.

---

<div align="center">

[⬆️ Back to top](#top)

</div>
