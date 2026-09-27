# 15-Day Learning Tracker Website --- Project Specification

## 1. Project overview

Build a lightweight, responsive website that runs locally and helps a
learner track a 15-day study plan across three learning tracks:

1.  **AWS CloudOps certification**
2.  **Kubernetes**
3.  **Generative AI (GenAI)**

The learner has approximately four years of AWS DevOps experience. The
website should make it easy to see each day's topics, mark topics as
completed, track progress, and keep progress after refreshing or
restarting the browser.

## 2. Suggested technology

Use a simple local web stack:

-   **Frontend:** HTML, CSS, and vanilla JavaScript, or React with Vite.
-   **Persistence:** Browser `localStorage` for a no-backend local
    version.
-   **Run locally:** Provide clear install and start commands in the
    README.
-   **No account or cloud service required.**

If using React, organize the project into reusable components. Keep the
implementation beginner-friendly and easy to modify.

## 3. Main features

### Dashboard

Show:

-   Title: **15-Day Learning Tracker**
-   Start date (user-selectable)
-   Current study day, based on the selected start date
-   Overall completion percentage and completed/total topic count
-   Separate progress indicators for CloudOps, Kubernetes, and GenAI
-   A 15-day overview with each day's status: Not started, In progress,
    or Completed
-   A "Continue today" button that opens the current day

### Daily checklist

Each day should display the three learning tracks with topic checkboxes.

For every topic, support:

-   Mark complete/incomplete
-   Optional notes
-   Optional resource link
-   Completion state saved automatically

Show a daily progress indicator and mark a day complete when all its
topics are checked. A day with some completed topics should show "In
progress."

### Calendar and navigation

-   Provide navigation between Day 1 and Day 15.
-   Allow selecting any day from a day list or calendar-like grid.
-   Clearly highlight today's planned day.
-   Allow users to review or complete previous days without blocking
    future days.

### Progress and reset

-   Save progress in `localStorage`.
-   Restore saved progress on page reload.
-   Include a reset action with a confirmation dialog.
-   Include an export option to download progress as JSON.
-   Include an import option to restore a previously exported JSON
    backup.

### User experience

-   Responsive layout for desktop, tablet, and mobile.
-   Accessible labels for checkboxes and buttons.
-   Clear visual distinction between incomplete and completed tasks.
-   Avoid unnecessary animations.
-   Include empty states and helpful feedback.

## 4. 15-day learning plan

Use the following default topics. Make the topic data easy to edit in
one file.

### Day 1 --- Foundations

**CloudOps** - Review the certification exam guide and objectives - Take
a baseline practice test - Identify weak areas

**Kubernetes** - Understand Kubernetes architecture - Learn the control
plane and worker nodes - Review Pods and Nodes

**GenAI** - Understand AI, machine learning, deep learning, and GenAI -
Learn basic LLM concepts

### Day 2 --- Observability and workloads

**CloudOps** - CloudWatch metrics, logs, and alarms - CloudTrail
fundamentals

**Kubernetes** - Pods - Deployments and ReplicaSets

**GenAI** - Tokens and context windows - Basic LLM API concepts

### Day 3 --- Compute and services

**CloudOps** - EC2 operations and troubleshooting - AWS Systems Manager
basics

**Kubernetes** - Services: ClusterIP, NodePort, and LoadBalancer

**GenAI** - Prompt engineering - Structured outputs

### Day 4 --- Availability and configuration

**CloudOps** - Auto Scaling - Load balancing and high availability

**Kubernetes** - ConfigMaps and Secrets - Liveness, readiness, and
startup probes

**GenAI** - Embeddings - Semantic search

### Day 5 --- Security and retrieval

**CloudOps** - IAM policies and roles - KMS and security controls

**Kubernetes** - Namespaces and RBAC - Resource requests and limits

**GenAI** - RAG architecture - Document retrieval fundamentals

### Day 6 --- Networking and first application

**CloudOps** - VPCs and routing - Security groups, NAT, and DNS

**Kubernetes** - Deploy an application - Expose it with a Service

**GenAI** - Build a simple application using an LLM API

### Day 7 --- Resilience and storage

**CloudOps** - AWS Backup - Disaster recovery and resilience

**Kubernetes** - PersistentVolumes and PersistentVolumeClaims -
StorageClasses

**GenAI** - Build a small RAG workflow using sample documents

### Day 8 --- Automation and packaging

**CloudOps** - CloudFormation fundamentals - Systems Manager automation

**Kubernetes** - Helm charts - Install and upgrade a chart

**GenAI** - Function calling and tool use

### Day 9 --- Optimization and scaling

**CloudOps** - Cost optimization - Performance troubleshooting

**Kubernetes** - Horizontal Pod Autoscaler - Rolling updates and
rollbacks

**GenAI** - LLM evaluation basics - Hallucinations and guardrails

### Day 10 --- Review and integration

**CloudOps** - Review exam domains - Complete targeted practice
questions

**Kubernetes** - EKS fundamentals - AWS IAM integration and networking
concepts

**GenAI** - Build a small RAG application - Test retrieval quality

### Day 11 --- Practice and troubleshooting

**CloudOps** - Complete a timed practice exam - Review every incorrect
answer

**Kubernetes** - Troubleshoot CrashLoopBackOff - Troubleshoot Pending
Pods and DNS issues

**GenAI** - Improve the RAG application - Test answers against a small
evaluation set

### Day 12 --- Weak areas and deployment

**CloudOps** - Revise weak exam domains - Review key AWS operational
services

**Kubernetes** - Ingress - NetworkPolicies and resource management

**GenAI** - Containerize the application with Docker - Prepare
deployment configuration

### Day 13 --- Mock exam and project

**CloudOps** - Complete a second timed practice exam - Review missed
questions and concepts

**Kubernetes** - Deploy the application to a local cluster or EKS -
Verify access and health checks

**GenAI** - Add logging and error handling - Write project documentation

### Day 14 --- Final review

**CloudOps** - Review weak areas - Assess exam readiness

**Kubernetes** - Revise core commands and concepts - Troubleshoot the
deployed application

**GenAI** - Finalize the project - Document the architecture and setup

### Day 15 --- Exam and wrap-up

**CloudOps** - Take the certification exam if ready - Record the result
and next steps

**Kubernetes** - Review essential commands - Record remaining topics to
practice

**GenAI** - Review the project - List next improvements

## 5. Data model

Use a data structure similar to this:

``` json
{
  "startDate": "YYYY-MM-DD",
  "topics": {
    "day-1-cloudops-1": {
      "completed": false,
      "notes": "",
      "resourceUrl": ""
    }
  }
}
```

Each topic should have a stable unique ID, day number, track, title, and
optional description. Store completion state and notes separately from
the static topic definitions where practical.

## 6. Suggested screens and components

-   `Dashboard`: overall progress and day overview
-   `DayView`: selected day's topic checklist
-   `TrackSection`: checklist grouped by learning track
-   `ProgressBar`: completion percentage
-   `DayNavigation`: day selector
-   `Settings`: start date, export/import, and reset
-   `topicData`: editable 15-day topic plan
-   `storage`: localStorage read/write helpers

## 7. Acceptance criteria

The website is complete when:

-   [ ] All 15 days appear in the dashboard.
-   [ ] Each day contains CloudOps, Kubernetes, and GenAI topics.
-   [ ] A topic can be checked and unchecked.
-   [ ] Progress updates immediately when a topic changes.
-   [ ] Daily and track-level progress are calculated correctly.
-   [ ] Overall progress is calculated from completed topics.
-   [ ] Progress remains after refreshing the page.
-   [ ] Users can navigate between all 15 days.
-   [ ] Users can edit and save notes for topics.
-   [ ] Users can export and import progress.
-   [ ] Reset requires confirmation.
-   [ ] The layout works on mobile and desktop.
-   [ ] The app runs locally using documented commands.

## 8. Deliverables

Provide:

1.  Complete source code.
2.  A `README.md` with prerequisites and local setup instructions.
3.  The editable 15-day topic data.
4.  A brief explanation of how progress is saved and how to back it up.

## 9. Important implementation notes

-   This is a personal learning tracker, not an official certification
    platform.
-   Do not claim that completing the checklist guarantees passing an
    exam.
-   Keep the study plan editable because certification objectives and
    personal priorities can change.
-   Make it possible to change the start date without deleting completed
    progress.
