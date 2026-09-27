"""The default 20-day study plan, copied into a new account on request.

Structure: a day holds **main tasks**, each holding **subtasks**. The three
study areas — AWS CloudOps, Kubernetes and GenAI — are main tasks, so the same
shape serves this plan, an uploaded CSV, or one built by hand.

Editing this file changes what new plans are seeded from. Existing users own
their own copy and are never affected, so their progress is safe.
"""

DEFAULT_PLAN: list[dict] = [
    {
        "title": 'Foundations',
        "tasks": [
            {
                "title": 'AWS CloudOps',
                "subtasks": [
                    'Review the certification exam guide and objectives',
                    'Take a baseline practice test',
                    'Identify weak areas',
                ],
            },
            {
                "title": 'Kubernetes',
                "subtasks": [
                    'Understand Kubernetes architecture',
                    'Learn the control plane and worker nodes',
                    'Review Pods and Nodes',
                ],
            },
            {
                "title": 'GenAI',
                "subtasks": [
                    'Understand AI, machine learning, deep learning, and GenAI',
                    'Learn basic LLM concepts',
                ],
            },
        ],
    },
    {
        "title": 'Observability and workloads',
        "tasks": [
            {
                "title": 'AWS CloudOps',
                "subtasks": [
                    'CloudWatch metrics, logs, and alarms',
                    'CloudTrail fundamentals',
                ],
            },
            {
                "title": 'Kubernetes',
                "subtasks": [
                    'Pods',
                    'Deployments and ReplicaSets',
                ],
            },
            {
                "title": 'GenAI',
                "subtasks": [
                    'Tokens and context windows',
                    'Basic LLM API concepts',
                ],
            },
        ],
    },
    {
        "title": 'Compute and services',
        "tasks": [
            {
                "title": 'AWS CloudOps',
                "subtasks": [
                    'EC2 operations and troubleshooting',
                    'AWS Systems Manager basics',
                ],
            },
            {
                "title": 'Kubernetes',
                "subtasks": [
                    'Services: ClusterIP, NodePort, and LoadBalancer',
                ],
            },
            {
                "title": 'GenAI',
                "subtasks": [
                    'Prompt engineering',
                    'Structured outputs',
                ],
            },
        ],
    },
    {
        "title": 'Availability and configuration',
        "tasks": [
            {
                "title": 'AWS CloudOps',
                "subtasks": [
                    'Auto Scaling',
                    'Load balancing and high availability',
                ],
            },
            {
                "title": 'Kubernetes',
                "subtasks": [
                    'ConfigMaps and Secrets',
                    'Liveness, readiness, and startup probes',
                ],
            },
            {
                "title": 'GenAI',
                "subtasks": [
                    'Embeddings',
                    'Semantic search',
                ],
            },
        ],
    },
    {
        "title": 'Security and retrieval',
        "tasks": [
            {
                "title": 'AWS CloudOps',
                "subtasks": [
                    'IAM policies and roles',
                    'KMS and security controls',
                ],
            },
            {
                "title": 'Kubernetes',
                "subtasks": [
                    'Namespaces and RBAC',
                    'Resource requests and limits',
                ],
            },
            {
                "title": 'GenAI',
                "subtasks": [
                    'RAG architecture',
                    'Document retrieval fundamentals',
                ],
            },
        ],
    },
    {
        "title": 'Networking and first application',
        "tasks": [
            {
                "title": 'AWS CloudOps',
                "subtasks": [
                    'VPCs and routing',
                    'Security groups, NAT, and DNS',
                ],
            },
            {
                "title": 'Kubernetes',
                "subtasks": [
                    'Deploy an application',
                    'Expose it with a Service',
                ],
            },
            {
                "title": 'GenAI',
                "subtasks": [
                    'Build a simple application using an LLM API',
                ],
            },
        ],
    },
    {
        "title": 'Resilience and storage',
        "tasks": [
            {
                "title": 'AWS CloudOps',
                "subtasks": [
                    'AWS Backup',
                    'Disaster recovery and resilience',
                ],
            },
            {
                "title": 'Kubernetes',
                "subtasks": [
                    'PersistentVolumes and PersistentVolumeClaims',
                    'StorageClasses',
                ],
            },
            {
                "title": 'GenAI',
                "subtasks": [
                    'Build a small RAG workflow using sample documents',
                ],
            },
        ],
    },
    {
        "title": 'Automation and packaging',
        "tasks": [
            {
                "title": 'AWS CloudOps',
                "subtasks": [
                    'CloudFormation fundamentals',
                    'Systems Manager automation',
                ],
            },
            {
                "title": 'Kubernetes',
                "subtasks": [
                    'Helm charts',
                    'Install and upgrade a chart',
                ],
            },
            {
                "title": 'GenAI',
                "subtasks": [
                    'Function calling and tool use',
                ],
            },
        ],
    },
    {
        "title": 'Optimization and scaling',
        "tasks": [
            {
                "title": 'AWS CloudOps',
                "subtasks": [
                    'Cost optimization',
                    'Performance troubleshooting',
                ],
            },
            {
                "title": 'Kubernetes',
                "subtasks": [
                    'Horizontal Pod Autoscaler',
                    'Rolling updates and rollbacks',
                ],
            },
            {
                "title": 'GenAI',
                "subtasks": [
                    'LLM evaluation basics',
                    'Hallucinations and guardrails',
                ],
            },
        ],
    },
    {
        "title": 'Review and integration',
        "tasks": [
            {
                "title": 'AWS CloudOps',
                "subtasks": [
                    'Review exam domains',
                    'Complete targeted practice questions',
                ],
            },
            {
                "title": 'Kubernetes',
                "subtasks": [
                    'EKS fundamentals',
                    'AWS IAM integration and networking concepts',
                ],
            },
            {
                "title": 'GenAI',
                "subtasks": [
                    'Build a small RAG application',
                    'Test retrieval quality',
                ],
            },
        ],
    },
    {
        "title": 'Practice and troubleshooting',
        "tasks": [
            {
                "title": 'AWS CloudOps',
                "subtasks": [
                    'Complete a timed practice exam',
                    'Review every incorrect answer',
                ],
            },
            {
                "title": 'Kubernetes',
                "subtasks": [
                    'Troubleshoot CrashLoopBackOff',
                    'Troubleshoot Pending Pods and DNS issues',
                ],
            },
            {
                "title": 'GenAI',
                "subtasks": [
                    'Improve the RAG application',
                    'Test answers against a small evaluation set',
                ],
            },
        ],
    },
    {
        "title": 'Weak areas and deployment',
        "tasks": [
            {
                "title": 'AWS CloudOps',
                "subtasks": [
                    'Revise weak exam domains',
                    'Review key AWS operational services',
                ],
            },
            {
                "title": 'Kubernetes',
                "subtasks": [
                    'Ingress',
                    'NetworkPolicies and resource management',
                ],
            },
            {
                "title": 'GenAI',
                "subtasks": [
                    'Containerize the application with Docker',
                    'Prepare deployment configuration',
                ],
            },
        ],
    },
    {
        "title": 'Mock exam and project',
        "tasks": [
            {
                "title": 'AWS CloudOps',
                "subtasks": [
                    'Complete a second timed practice exam',
                    'Review missed questions and concepts',
                ],
            },
            {
                "title": 'Kubernetes',
                "subtasks": [
                    'Deploy the application to a local cluster or EKS',
                    'Verify access and health checks',
                ],
            },
            {
                "title": 'GenAI',
                "subtasks": [
                    'Add logging and error handling',
                    'Write project documentation',
                ],
            },
        ],
    },
    {
        "title": 'Advanced networking and security',
        "tasks": [
            {
                "title": 'AWS CloudOps',
                "subtasks": [
                    'VPC peering and Transit Gateway',
                    'Security Hub, GuardDuty, and AWS Config',
                ],
            },
            {
                "title": 'Kubernetes',
                "subtasks": [
                    'Service mesh concepts and when to use one',
                    'Pod Security Standards and admission control',
                ],
            },
            {
                "title": 'GenAI',
                "subtasks": [
                    'Prompt injection and input validation',
                    'Handling PII and redaction',
                ],
            },
        ],
    },
    {
        "title": 'Observability and cost at scale',
        "tasks": [
            {
                "title": 'AWS CloudOps',
                "subtasks": [
                    'CloudWatch dashboards and composite alarms',
                    'Cost allocation tags and budgets',
                ],
            },
            {
                "title": 'Kubernetes',
                "subtasks": [
                    'Metrics Server and Prometheus basics',
                    'Cluster logging with Fluent Bit',
                ],
            },
            {
                "title": 'GenAI',
                "subtasks": [
                    'Tracking token usage and cost',
                    'Caching and batching to reduce spend',
                ],
            },
        ],
    },
    {
        "title": 'Automation and delivery',
        "tasks": [
            {
                "title": 'AWS CloudOps',
                "subtasks": [
                    'CodePipeline and CodeBuild',
                    'Blue/green and canary deployments',
                ],
            },
            {
                "title": 'Kubernetes',
                "subtasks": [
                    'GitOps with Argo CD or Flux',
                    'Kustomize overlays per environment',
                ],
            },
            {
                "title": 'GenAI',
                "subtasks": [
                    'Run an evaluation suite in CI',
                    'Regression tests for prompt changes',
                ],
            },
        ],
    },
    {
        "title": 'Capstone build',
        "tasks": [
            {
                "title": 'AWS CloudOps',
                "subtasks": [
                    'Provision the capstone environment with IaC',
                    'Wire up monitoring and alerting',
                ],
            },
            {
                "title": 'Kubernetes',
                "subtasks": [
                    'Deploy the capstone to a cluster',
                    'Tune autoscaling and resource requests',
                ],
            },
            {
                "title": 'GenAI',
                "subtasks": [
                    'Build the capstone retrieval service',
                    'Add streaming responses',
                ],
            },
        ],
    },
    {
        "title": 'Capstone hardening',
        "tasks": [
            {
                "title": 'AWS CloudOps',
                "subtasks": [
                    'Run a failure drill and document the recovery',
                    'Review IAM for least privilege',
                ],
            },
            {
                "title": 'Kubernetes',
                "subtasks": [
                    'Add NetworkPolicies and PodDisruptionBudgets',
                    'Verify a rollout and a rollback',
                ],
            },
            {
                "title": 'GenAI',
                "subtasks": [
                    'Add guardrails and rate limiting',
                    'Load test and tune latency',
                ],
            },
        ],
    },
    {
        "title": 'Final review',
        "tasks": [
            {
                "title": 'AWS CloudOps',
                "subtasks": [
                    'Review weak areas',
                    'Assess exam readiness',
                ],
            },
            {
                "title": 'Kubernetes',
                "subtasks": [
                    'Revise core commands and concepts',
                    'Troubleshoot the deployed application',
                ],
            },
            {
                "title": 'GenAI',
                "subtasks": [
                    'Finalize the project',
                    'Document the architecture and setup',
                ],
            },
        ],
    },
    {
        "title": 'Exam and wrap-up',
        "tasks": [
            {
                "title": 'AWS CloudOps',
                "subtasks": [
                    'Take the certification exam if ready',
                    'Record the result and next steps',
                ],
            },
            {
                "title": 'Kubernetes',
                "subtasks": [
                    'Review essential commands',
                    'Record remaining topics to practice',
                ],
            },
            {
                "title": 'GenAI',
                "subtasks": [
                    'Review the project',
                    'List next improvements',
                ],
            },
        ],
    },
]
