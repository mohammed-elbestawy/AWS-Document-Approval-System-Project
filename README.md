# AWS Document Approval System

A fully serverless document approval workflow built on AWS. Users submit PDF documents through a secure HTTPS frontend, an approver receives email links to approve or reject the document, and the final decision is stored in DynamoDB.

![AWS](https://img.shields.io/badge/AWS-Serverless-FF9900?style=flat&logo=amazonaws&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)

## Overview

1. User opens the web application.
2. User submits a document.
3. The document is stored in private S3.
4. Metadata is stored in DynamoDB with `PENDING` status.
5. SNS sends the approval notification.
6. The approver receives Approve / Reject links.
7. The link contains `doc_id`, `token`, and `action`.
8. `decision-handler` validates the token.
9. DynamoDB changes to `APPROVED` or `REJECTED`.
10. A result notification is sent through SNS.

## Architecture

![Architecture Diagram](screenshots/architecture-diagram.png)

```text
User
  ↓
CloudFront + OAC
  ↓
Private S3 (Frontend)
  ↓
Browser Frontend
  ↓ POST /submit
API Gateway
  ↓
submit-handler Lambda
  ├──→ S3 (Private Documents)
  ├──→ DynamoDB (PENDING)
  └──→ SNS → Approver Email
                    ↓
              Approve / Reject
                    ↓
             GET /decision
                    ↓
               API Gateway
                    ↓
          decision-handler Lambda
             ├──→ DynamoDB
             │    APPROVED / REJECTED
             └──→ SNS
                    ↓
             Result Notification
```

## AWS Services

| Layer | Service | Purpose |
|---|---|---|
| Frontend | S3 + CloudFront | Static frontend over HTTPS |
| S3 security | CloudFront OAC | Keeps frontend bucket private |
| API | API Gateway REST | `/submit` and `/decision` |
| Compute | Lambda | Submission and decision logic |
| Documents | S3 | Private PDF storage |
| Database | DynamoDB | Metadata, status, token |
| Notifications | SNS | Email notifications |
| Permissions | IAM | Lambda execution permissions |

**Region:** `eu-north-1`

## API Endpoints

### `POST /submit`

Receives the submission from the browser and invokes `submit-handler`.

### `GET /decision`

Used by the Approve / Reject links.

```text
/decision?doc_id=<ID>&token=<TOKEN>&action=approve
```

## DynamoDB

Table:

```text
document-approvals
```

Partition key:

```text
doc_id (String)
```

Capacity mode:

```text
On-demand
```

State transition:

```text
PENDING → APPROVED
PENDING → REJECTED
```

## Approval Token

The project intentionally does not use Cognito for the simple single-approver workflow.

A random decision token is generated for each document and stored in DynamoDB. The token is included in the approval link.

The Lambda verifies:

```text
token from URL == token stored in DynamoDB
```

Knowing only the `doc_id` is not enough to approve or reject a document.

## Security

- Private S3 frontend bucket
- CloudFront Origin Access Control
- HTTPS
- Restricted CORS origin
- Server-side validation
- Allowed actions limited to `approve` and `reject`
- `PENDING` status check
- Generic client errors with detailed CloudWatch logging
- IAM permissions scoped to the resources where supported

## Live Test

The final test checks:

| Check | Expected |
|---|---|
| CloudFront URL | Frontend loads |
| PDF submission | Success |
| DynamoDB | `PENDING` |
| Approver email | Approve / Reject links |
| Approval link | Confirmation HTML page |
| DynamoDB | `APPROVED` or `REJECTED` |
| Result notification | Sent |

Screenshots:

```text
screenshots/12-fulltest-submit.png
screenshots/12-fulltest-approval-email.png
screenshots/12-fulltest-decision-page.png
screenshots/12-fulltest-dynamodb-status.png
```

## Repository Structure

```text
AWS-Document-Approval-System-Project/
├── README.md
├── STEPS.md
├── CONCEPTS.md
├── screenshots/
├── code/
│   ├── frontend/
│   │   └── index.html
│   └── lambda/
│       ├── submit_handler.py
│       └── decision_handler.py
└── iam/
    └── document-approval-lambda-policy.json
```

## Cost Management

The project has no EC2 instances or load balancers. The services are serverless and usage-based.

Actual charges depend on AWS usage, data transfer, storage, current Free Tier eligibility, and account configuration. For a small personal test workload, usage should be very low.

## Possible Improvements

- Cognito for authenticated multi-user approval
- Token expiration
- Conditional DynamoDB updates
- AWS WAF and API throttling
- Terraform / CloudFormation
- CloudWatch dashboards and alarms
- Separate notification topics for approver and submitter
