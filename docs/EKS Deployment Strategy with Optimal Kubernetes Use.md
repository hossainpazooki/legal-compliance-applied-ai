# EKS Deployment Strategy with Optimal Kubernetes Use

## Table of Contents

1. [Overview](#overview)
2. [Architecture Overview](#architecture-overview)
3. [Directory Structure](#directory-structure)
4. [Core Kubernetes Manifests](#core-kubernetes-manifests)
   - [Namespace](#namespace)
   - [API Deployment](#api-deployment)
   - [API Service](#api-service)
   - [API ConfigMap](#api-configmap)
   - [API HPA](#api-hpa-horizontal-pod-autoscaler)
   - [Worker Deployment](#worker-deployment)
   - [External Secrets](#external-secrets-aws-secrets-manager-integration)
   - [ALB Ingress](#alb-ingress)
5. [Temporal Helm Deployment](#temporal-helm-deployment)
6. [Kustomize Configuration](#kustomize-configuration)
7. [EKS Cluster Setup (Terraform)](#eks-cluster-setup-terraform)
8. [CI/CD Pipeline Architecture](#cicd-pipeline-architecture)
9. [Cost Estimate](#cost-estimate-eks)
10. [Key Kubernetes Best Practices](#key-kubernetes-best-practices-used)
11. [Quick Commands Reference](#quick-commands-reference)
12. [EKS Migration Checklist](#eks-migration-checklist)
13. [References](#references)

---

## Overview

This document describes the Kubernetes deployment architecture for the Legal Compliance AI platform on Amazon EKS (Elastic Kubernetes Service). The architecture follows AWS best practices for security, scalability, and operational excellence while leveraging Kubernetes-native patterns for workload management.

**Key Design Principles:**
- **Infrastructure as Code**: All Kubernetes manifests managed via Kustomize with environment overlays
- **Defense in Depth**: Multiple security layers (pod security, network policies, IRSA, secrets management)
- **High Availability**: Multi-AZ deployment with topology spread constraints and horizontal pod autoscaling
- **GitOps Ready**: Declarative configuration that enables ArgoCD or Flux integration
- **Cost Optimization**: Right-sized resources with autoscaling to match actual demand

---

## Architecture Overview

The architecture consists of three main layers:

1. **Ingress Layer**: AWS Application Load Balancer (ALB) managed by the ALB Ingress Controller handles external HTTPS traffic, terminates TLS, and routes requests to backend services based on hostname rules.

2. **Application Layer**: The `legal-compliance` namespace contains three deployments:
   - **API**: FastAPI backend (3 replicas) serving REST endpoints for rule evaluation, decision making, and compliance workflows
   - **Worker**: Temporal workflow workers (2 replicas) that execute long-running compliance analysis and document processing tasks
   - **Frontend**: React application (2 replicas) served via nginx for the user interface

3. **Persistence Layer**: AWS managed services provide durable storage:
   - **RDS PostgreSQL (app-db)**: Stores rules, decisions, audit logs, and application state
   - **RDS PostgreSQL (temporal-db)**: Temporal workflow engine persistence (history, timers, task queues)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS EKS Cluster                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        ALB Ingress Controller                        │    │
│  └───────────────────────────────┬─────────────────────────────────────┘    │
│                                  │                                           │
│  ┌───────────────────────────────┼───────────────────────────────────────┐  │
│  │  Namespace: legal-compliance  │                                        │  │
│  │  ┌────────────────┐    ┌──────▼───────┐    ┌────────────────┐         │  │
│  │  │   Deployment   │    │  Deployment  │    │   Deployment   │         │  │
│  │  │    worker      │    │     api      │    │   frontend     │         │  │
│  │  │   replicas: 2  │    │  replicas: 3 │    │  replicas: 2   │         │  │
│  │  └───────┬────────┘    └──────┬───────┘    └────────────────┘         │  │
│  │          │                    │                                        │  │
│  │          │         ┌──────────┴──────────┐                            │  │
│  │          │         │    Service (ClusterIP)                           │  │
│  │          │         │    api-service:8000                              │  │
│  └──────────┼─────────┴─────────────────────────────────────────────────┘  │
│             │                                                               │
│  ┌──────────┼───────────────────────────────────────────────────────────┐  │
│  │  Namespace: temporal          │                                       │  │
│  │  ┌────────────────┐    ┌──────▼───────┐    ┌────────────────┐        │  │
│  │  │   Temporal     │    │   Temporal   │    │   Temporal     │        │  │
│  │  │   Frontend     │    │    Server    │    │    History     │        │  │
│  │  │   (UI)         │    │              │    │    Matching    │        │  │
│  │  └────────────────┘    └──────┬───────┘    └────────────────┘        │  │
│  │                               │                                       │  │
│  └───────────────────────────────┼───────────────────────────────────────┘  │
│                                  │                                           │
│  ┌───────────────────────────────┼───────────────────────────────────────┐  │
│  │  AWS Managed Services         │                                        │  │
│  │  ┌────────────────┐    ┌──────▼───────┐                               │  │
│  │  │ RDS PostgreSQL │    │ RDS PostgreSQL│                              │  │
│  │  │   app-db       │    │  temporal-db  │                              │  │
│  │  └────────────────┘    └───────────────┘                              │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

The Kubernetes manifests follow the **Kustomize base/overlay pattern**, which enables DRY (Don't Repeat Yourself) configuration management across environments. This pattern is the recommended approach for EKS deployments as it integrates natively with `kubectl` and enables GitOps workflows.

**Why Kustomize over Helm?**
- **No templating complexity**: Pure YAML with strategic merge patches
- **Native kubectl support**: Built into `kubectl apply -k` since Kubernetes 1.14
- **Environment parity**: Same base manifests across all environments
- **Easier auditing**: Clear diff between environments via overlay patches

```
kube/
├── base/                         # Shared Kubernetes manifests (environment-agnostic)
│   ├── kustomization.yaml        # Base config, lists all resources to include
│   ├── namespace.yaml            # legal-compliance namespace definition
│   ├── api/
│   │   ├── deployment.yaml       # API pods (3 replicas default)
│   │   ├── service.yaml          # ClusterIP service for internal routing
│   │   ├── hpa.yaml              # HorizontalPodAutoscaler (2-10 replicas)
│   │   └── external-secret.yaml  # AWS Secrets Manager integration via ESO
│   ├── worker/
│   │   ├── deployment.yaml       # Temporal worker pods (no service - outbound only)
│   │   └── hpa.yaml              # Worker autoscaling based on CPU
│   └── frontend/
│       ├── deployment.yaml       # nginx serving React static assets
│       ├── service.yaml          # ClusterIP for ALB target group
│       └── hpa.yaml              # Frontend autoscaling
│
└── overlays/                     # Environment-specific overrides (patches)
    ├── dev/
    │   ├── kustomization.yaml    # Dev: latest tags, 1 replica, reduced resources
    │   ├── configmap.yaml        # Dev: DEBUG logging, localhost CORS
    │   ├── ingress.yaml          # Dev: internal ALB, no TLS requirement
    │   └── egress.yaml           # Dev: permissive outbound rules
    └── prod/
        ├── kustomization.yaml    # Prod: semantic version tags, full replicas
        ├── configmap.yaml        # Prod: WARNING logging, production domains
        ├── ingress.yaml          # Prod: internet-facing ALB, ACM TLS cert
        └── egress.yaml           # Prod: restricted outbound (RDS, Temporal only)
```

**Note**: Staging and UAT overlays were removed as they are not needed for this deployment. The two-environment model (dev/prod) simplifies operations while maintaining sufficient isolation for testing.

---

## Core Kubernetes Manifests

This section details the key Kubernetes resources with explanations of the configuration choices. Each manifest demonstrates production-grade patterns for security, reliability, and observability.

### Namespace

Namespaces provide logical isolation within the cluster. The `legal-compliance` namespace isolates our workloads from other applications and enables:
- **Resource quotas**: Limit CPU/memory consumption per namespace
- **Network policies**: Control traffic flow between namespaces
- **RBAC scoping**: Grant permissions only within this namespace
- **Cost allocation**: Track resource usage per namespace via tags

```yaml
# kube/base/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: legal-compliance
  labels:
    app.kubernetes.io/name: legal-compliance
    app.kubernetes.io/part-of: legal-compliance-platform
```

### API Deployment

The API deployment is the core backend service. Key configuration choices explained:

| Configuration | Purpose |
|--------------|---------|
| `replicas: 3` | Minimum for high availability across 3 AZs |
| `serviceAccountName: api-sa` | Required for IRSA (IAM Roles for Service Accounts) |
| `envFrom` | Inject config from ConfigMap and secrets without hardcoding |
| `resources.requests` | Guaranteed CPU/memory for scheduling decisions |
| `resources.limits` | Hard cap to prevent noisy neighbor issues |
| `livenessProbe` | Restart unhealthy containers (detects deadlocks) |
| `readinessProbe` | Remove from load balancer during startup/issues |
| `securityContext` | Defense in depth - non-root, read-only filesystem |
| `topologySpreadConstraints` | Distribute pods across availability zones |

```yaml
# kube/base/api/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: legal-compliance
  labels:
    app: api
    app.kubernetes.io/name: api
    app.kubernetes.io/component: backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: api-sa
      containers:
        - name: api
          image: <AWS_ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/legal-compliance-api:latest
          ports:
            - containerPort: 8000
              name: http
          envFrom:
            - configMapRef:
                name: api-config
            - secretRef:
                name: api-secrets
          resources:
            requests:
              cpu: "250m"
              memory: "512Mi"
            limits:
              cpu: "1000m"
              memory: "1Gi"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            readOnlyRootFilesystem: true
            allowPrivilegeEscalation: false
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: api
```

### API Service

Services provide stable network endpoints for pods. The API uses `ClusterIP` type because:
- **Internal only**: No direct external access - all traffic flows through the ALB Ingress
- **Load balancing**: Kubernetes automatically distributes requests across healthy pods
- **Service discovery**: Other pods can reach the API at `api.legal-compliance.svc.cluster.local:8000`

**Why not LoadBalancer type?** Using `ClusterIP` with ALB Ingress is more cost-effective and secure than individual LoadBalancer services. Multiple services can share a single ALB.

```yaml
# kube/base/api/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: legal-compliance
  labels:
    app: api
spec:
  type: ClusterIP
  ports:
    - port: 8000
      targetPort: 8000
      protocol: TCP
      name: http
  selector:
    app: api
```

### API ConfigMap

ConfigMaps store non-sensitive configuration that varies between environments. This base ConfigMap contains shared settings; environment-specific values are patched via overlays.

**ConfigMap vs Environment Variables:**
- ConfigMaps enable configuration changes without rebuilding images
- Multiple pods share the same ConfigMap (single source of truth)
- Changes trigger rolling updates when pod spec references change

**Note**: Sensitive values (DATABASE_URL, API keys) go in Secrets, not ConfigMaps.

```yaml
# kube/base/api/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-config
  namespace: legal-compliance
data:
  ENABLE_VECTOR_SEARCH: "true"
  TEMPORAL_NAMESPACE: "default"
  TEMPORAL_TASK_QUEUE: "compliance-workflows"
  TEMPORAL_HOST: "temporal-frontend.temporal.svc.cluster.local:7233"
  CORS_ORIGINS: "https://legal-compliance.example.com,https://digital-assets-cross-border.vercel.app"
```

### API HPA (Horizontal Pod Autoscaler)

HPA automatically adjusts replica count based on observed metrics. This enables cost optimization (fewer pods during low traffic) while maintaining performance during spikes.

**Scaling Configuration Explained:**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `minReplicas: 2` | Always maintain 2 pods for availability |
| `maxReplicas: 10` | Cap to prevent runaway scaling costs |
| `cpu.averageUtilization: 70%` | Scale up before saturation (80-90% is too late) |
| `memory.averageUtilization: 80%` | Memory often correlates with request load |
| `scaleDown.stabilizationWindowSeconds: 300` | Wait 5 minutes before scaling down (prevents flapping) |
| `scaleUp.stabilizationWindowSeconds: 0` | Scale up immediately when needed |
| `scaleDown.policies: 10%/60s` | Gradual scale-down (remove max 10% per minute) |
| `scaleUp.policies: 100%/15s` | Aggressive scale-up (double every 15 seconds if needed) |

**Why asymmetric scaling?** Scale-up should be fast to handle traffic spikes. Scale-down should be slow to avoid premature pod termination during brief traffic lulls.

```yaml
# kube/base/api/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
  namespace: legal-compliance
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
```

### Worker Deployment

Workers are Temporal workflow executors that process long-running compliance tasks. Unlike the API, workers:
- **Have no Service**: Workers poll Temporal for tasks; they don't receive inbound traffic
- **No health probes (TODO)**: Workers should add TCP probes to Temporal client connection
- **Different resource profile**: Lower memory, CPU matches API for rule evaluation

**Worker vs API Scaling:**
- API scales with HTTP request load (CPU/memory utilization)
- Workers scale with task queue depth (Temporal metrics)
- In production, consider using Temporal's SDK metrics for HPA custom metrics

```yaml
# kube/base/worker/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker
  namespace: legal-compliance
  labels:
    app: worker
    app.kubernetes.io/name: worker
    app.kubernetes.io/component: temporal-worker
spec:
  replicas: 2
  selector:
    matchLabels:
      app: worker
  template:
    metadata:
      labels:
        app: worker
    spec:
      serviceAccountName: worker-sa
      containers:
        - name: worker
          image: <AWS_ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/legal-compliance-worker:latest
          envFrom:
            - configMapRef:
                name: api-config
            - secretRef:
                name: api-secrets
          resources:
            requests:
              cpu: "250m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            allowPrivilegeEscalation: false
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: worker
```

### External Secrets (AWS Secrets Manager Integration)

External Secrets Operator (ESO) synchronizes secrets from AWS Secrets Manager into Kubernetes Secrets. This pattern is **essential for EKS** because:

1. **No secrets in Git**: Sensitive values stored in AWS, not in manifests
2. **Automatic rotation**: ESO polls for changes (configurable `refreshInterval`)
3. **Centralized management**: Secrets managed via AWS Console, CLI, or Terraform
4. **Audit trail**: AWS CloudTrail logs all secret access

**Prerequisites:**
- External Secrets Operator installed in cluster
- ClusterSecretStore configured with IRSA role for Secrets Manager access
- Secrets created in AWS Secrets Manager with expected structure

**How it works:**
1. ExternalSecret resource references AWS secret by name/ARN
2. ESO controller (running in cluster) reads from AWS using IRSA credentials
3. ESO creates/updates a native Kubernetes Secret
4. Pods consume the Secret via `secretRef` (unchanged from regular secrets)

```yaml
# kube/base/api/external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: api-secrets
  namespace: legal-compliance
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: api-secrets
    creationPolicy: Owner
  data:
    - secretKey: DATABASE_URL
      remoteRef:
        key: legal-compliance/prod/database
        property: url
```

### ALB Ingress

The AWS Load Balancer Controller (formerly ALB Ingress Controller) provisions and configures AWS Application Load Balancers directly from Kubernetes Ingress resources.

**Why ALB over nginx-ingress?**
- **Native AWS integration**: Uses AWS WAF, Shield, ACM certificates
- **Cost efficiency**: One ALB can serve multiple services via rules
- **Health checks**: ALB health checks integrated with EKS target groups
- **Observability**: Metrics flow to CloudWatch automatically

**Key Annotations Explained:**

| Annotation | Value | Purpose |
|------------|-------|---------|
| `kubernetes.io/ingress.class: alb` | Select ALB controller (vs nginx) |
| `alb.ingress.kubernetes.io/scheme: internet-facing` | Public ALB (vs internal) |
| `alb.ingress.kubernetes.io/target-type: ip` | Route directly to pod IPs (required for Fargate) |
| `alb.ingress.kubernetes.io/certificate-arn` | ACM certificate for TLS termination |
| `alb.ingress.kubernetes.io/listen-ports` | HTTPS only (no HTTP listener) |
| `alb.ingress.kubernetes.io/ssl-redirect: "443"` | Redirect HTTP to HTTPS |
| `alb.ingress.kubernetes.io/healthcheck-path` | ALB health check endpoint |
| `alb.ingress.kubernetes.io/group.name` | Merge multiple Ingresses into one ALB |

```yaml
# kube/ingress/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: legal-compliance-ingress
  namespace: legal-compliance
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:REGION:ACCOUNT:certificate/CERT_ID
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/group.name: legal-compliance
spec:
  rules:
    - host: api.legal-compliance.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api
                port:
                  number: 8000
    - host: legal-compliance.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 80
```

---

## Temporal Helm Deployment

Temporal is the workflow orchestration engine that powers long-running compliance processes (document analysis, multi-step approvals, scheduled checks). Unlike application services managed via Kustomize, Temporal is deployed via its official Helm chart because:

1. **Complex dependencies**: Temporal has 4+ services (server, history, matching, worker) with intricate configuration
2. **Versioned releases**: Helm chart versions map to tested Temporal releases
3. **Operational patterns**: Built-in support for upgrades, rollbacks, and configuration management

**Temporal Components:**

| Component | Purpose |
|-----------|---------|
| `server` | Core workflow engine (gRPC API) |
| `history` | Workflow execution history storage |
| `matching` | Task queue management and distribution |
| `frontend` | Client-facing gRPC/HTTP API |
| `web` | Temporal UI for workflow visibility |
| `admintools` | CLI tools for debugging and migration |

**Why RDS for Temporal persistence?**
- **Durability**: Workflows are mission-critical; RDS provides Multi-AZ replication
- **Managed backups**: Automated snapshots without operational overhead
- **Performance**: PostgreSQL handles Temporal's write-heavy workload efficiently

```yaml
# kube/temporal/values.yaml
server:
  replicaCount: 3

  config:
    persistence:
      default:
        driver: sql
        sql:
          driver: postgres
          host: temporal-db.xxxxx.rds.amazonaws.com
          port: 5432
          database: temporal
          user: temporal
          existingSecret: temporal-db-credentials

  resources:
    requests:
      cpu: "500m"
      memory: "1Gi"
    limits:
      cpu: "2000m"
      memory: "2Gi"

admintools:
  enabled: true

web:
  enabled: true
  replicaCount: 2
  ingress:
    enabled: true
    className: alb
    hosts:
      - host: temporal.legal-compliance.example.com
        paths:
          - path: /
            pathType: Prefix

prometheus:
  enabled: true

grafana:
  enabled: false  # Use external Grafana

elasticsearch:
  enabled: false  # Optional: enable for advanced visibility
```

Install with:

```bash
helm repo add temporal https://charts.temporal.io
helm install temporal temporal/temporal \
  -n temporal \
  --create-namespace \
  -f kube/temporal/values.yaml
```

---

## Kustomize Configuration

Kustomize enables environment-specific configuration without duplicating YAML files. The base contains shared resources; overlays patch them for each environment.

**How Overlays Work:**

```
Base (shared)          Overlay (environment-specific)
     │                           │
     ▼                           ▼
Deployment:                patches:
  replicas: 3       +      - op: replace
  resources: high          path: /spec/replicas
                           value: 1

             ═══════════════════════
                        │
                        ▼
              Final Manifest:
                replicas: 1
                resources: high (inherited)
```

**Key Kustomize Features Used:**

| Feature | Purpose | Example |
|---------|---------|---------|
| `resources` | Include base manifests | `- ../../base` |
| `namespace` | Override namespace for all resources | `legal-compliance-dev` |
| `images` | Change image tags without editing deployments | `newTag: v1.2.3` |
| `replicas` | Scale deployments | `count: 1` for dev |
| `patches` | JSON patches for fine-grained changes | Resource limits |
| `commonLabels` | Add labels to all resources | `environment: prod` |
| `nameSuffix` | Append suffix to all resource names | `-dev` for isolation |

```yaml
# kube/base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: legal-compliance

resources:
  - namespace.yaml
  - api/deployment.yaml
  - api/service.yaml
  - api/configmap.yaml
  - api/hpa.yaml
  - api/external-secret.yaml
  - worker/deployment.yaml
  - worker/hpa.yaml
  - frontend/deployment.yaml
  - frontend/service.yaml

commonLabels:
  app.kubernetes.io/part-of: legal-compliance-platform
  app.kubernetes.io/managed-by: kustomize
```

```yaml
# kube/overlays/prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

namespace: legal-compliance

images:
  - name: <AWS_ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/legal-compliance-api
    newTag: v1.2.3
  - name: <AWS_ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/legal-compliance-worker
    newTag: v1.2.3

replicas:
  - name: api
    count: 3
  - name: worker
    count: 2

patches:
  - path: patches/api-resources.yaml
```

---

## EKS Cluster Setup (Terraform)

This section provides the Terraform configuration for provisioning the EKS cluster and supporting AWS infrastructure. The configuration uses the official terraform-aws-modules which encode AWS best practices.

**Key Architectural Decisions:**

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Compute | Managed Node Groups (EC2) | Better for predictable workloads, GPU support, cost optimization with Reserved Instances |
| Alternative | Fargate profiles | Serverless option - no node management, pay-per-pod, but limited customization |
| Networking | Private subnets | Pods run in private subnets; NAT Gateway for outbound internet |
| IAM | IRSA enabled | Pods assume IAM roles without node-level credentials |
| Add-ons | Managed | CoreDNS, kube-proxy, VPC CNI managed by EKS for automatic updates |

**IRSA (IAM Roles for Service Accounts):**

IRSA is the recommended way to grant AWS API access to pods. Instead of using node IAM roles (which grant all pods the same permissions), IRSA enables:
- **Least privilege**: Each service account gets only the permissions it needs
- **Auditability**: CloudTrail shows which pod/service account accessed AWS APIs
- **No long-lived credentials**: Temporary tokens via STS AssumeRoleWithWebIdentity

**Managed Node Groups vs Self-Managed:**
- Managed: AWS handles AMI updates, node draining, and lifecycle
- Self-managed: Full control but operational overhead
- Recommendation: Start with managed, move to self-managed only if specific customization needed

```hcl
# terraform/eks.tf
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = "legal-compliance-eks"
  cluster_version = "1.29"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # Fargate profiles for serverless pods
  fargate_profiles = {
    default = {
      name = "default"
      selectors = [
        { namespace = "legal-compliance" },
        { namespace = "temporal" }
      ]
    }
  }

  # Or managed node groups for EC2
  eks_managed_node_groups = {
    main = {
      instance_types = ["t3.medium", "t3a.medium"]

      min_size     = 2
      max_size     = 10
      desired_size = 3

      labels = {
        Environment = "production"
      }
    }
  }

  # Enable IRSA for pod IAM roles
  enable_irsa = true

  # Cluster addons
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }
}

# ALB Controller IAM Role
module "alb_controller_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"

  role_name = "alb-controller"

  attach_load_balancer_controller_policy = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:aws-load-balancer-controller"]
    }
  }
}

# RDS for app database
module "app_db" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"

  identifier = "legal-compliance-app"

  engine               = "postgres"
  engine_version       = "15"
  family               = "postgres15"
  major_engine_version = "15"
  instance_class       = "db.t3.medium"

  allocated_storage = 20

  db_name  = "legal_compliance"
  username = "app"
  port     = 5432

  vpc_security_group_ids = [module.security_group.security_group_id]
  db_subnet_group_name   = module.vpc.database_subnet_group_name

  backup_retention_period = 7
  deletion_protection     = true
}
```

---

## CI/CD Pipeline Architecture

The project includes a comprehensive CI/CD pipeline with GitHub Actions for automated testing, building, and deployment. The pipeline follows the **trunk-based development** model where:

- **Feature branches** are short-lived and merge to `main` via PR
- **Main branch** is always deployable and auto-deploys to staging
- **Production deploys** are manual with approval gates

**Pipeline Philosophy:**
1. **Fail fast**: Run cheap checks (lint, type-check) before expensive ones (tests, builds)
2. **Shift left security**: Security scanning in CI, not just before production
3. **Immutable artifacts**: Same Docker image flows from staging to production
4. **Automated rollback**: Failed production deploys automatically revert

### Pipeline Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          GitHub Actions Workflows                           │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PR/Push → [CI Pipeline] (.github/workflows/ci.yml)                         │
│            ├── Backend Tests (pytest, 706 tests)                            │
│            ├── Backend Lint (Ruff)                                          │
│            ├── Backend Type Check (mypy)                                    │
│            ├── Backend Security (Bandit)                                    │
│            ├── Frontend Lint & Build (ESLint, TypeScript)                   │
│            ├── Frontend Security (npm audit)                                │
│            └── Docker Build Validation (matrix build)                       │
│                                                                              │
│  main → [CD Staging] (.github/workflows/cd-staging.yml)                     │
│          ├── Build & Push to ECR (api, worker, frontend)                    │
│          ├── Scan Container Images (Trivy)                                  │
│          ├── Deploy to Staging (Kustomize)                                  │
│          ├── Run Smoke Tests                                                │
│          └── Slack Notification                                             │
│                                                                              │
│  manual → [CD Production] (.github/workflows/cd-production.yml)             │
│            ├── Validate Image Exists                                        │
│            ├── Deploy to Production (requires approval)                     │
│            ├── Production Validation                                        │
│            ├── Auto-Rollback on Failure                                     │
│            ├── Create GitHub Release                                        │
│            └── Slack Notification                                           │
│                                                                              │
│  weekly → [Security Scan] (.github/workflows/security-scan.yml)             │
│            ├── Dependency Vulnerability Scan (pip-audit, npm audit)         │
│            ├── SAST - Bandit + Semgrep                                      │
│            ├── Secret Scanning (Gitleaks)                                   │
│            ├── Container Image Scan (Trivy)                                 │
│            └── IaC Scan (Checkov)                                           │
│                                                                              │
└────────────────────────────────────────────────────────────────────────────┘
```

### Workflow Files

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `.github/workflows/ci.yml` | PR, Push to main/develop | Full test suite, linting, type checking, security |
| `.github/workflows/cd-staging.yml` | Push to main | Auto-deploy to staging with smoke tests |
| `.github/workflows/cd-production.yml` | Manual dispatch | Production deploy with approval gate |
| `.github/workflows/security-scan.yml` | Weekly + dependency changes | Comprehensive security audits |

### Required Secrets

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | IAM user for ECR/EKS access |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key |
| `CODECOV_TOKEN` | Code coverage reporting (optional) |
| `SLACK_WEBHOOK` | Slack notifications (optional) |
| `SEMGREP_APP_TOKEN` | Semgrep SAST (optional) |

### GitHub Environments

Create two environments in repository settings:

**Staging**
- No required reviewers
- Auto-deploy on main push

**Production**
- Required reviewers: 1-2 approvers
- Environment protection rules enabled
- Deployment branches: main only

### CI Pipeline Jobs

```yaml
# .github/workflows/ci.yml (summary)
jobs:
  backend-test:      # pytest with coverage
  backend-lint:      # Ruff linting
  backend-typecheck: # mypy type checking
  backend-security:  # Bandit security scan
  frontend-lint:     # ESLint + TypeScript + build
  frontend-security: # npm audit
  docker-build:      # Matrix build validation
  ci-status:         # Aggregate status check
```

### CD Staging Pipeline

Automatically triggered on push to main:

1. **Build & Push** - Build all 3 Docker images, push to ECR with SHA tag
2. **Scan Images** - Run Trivy vulnerability scanner
3. **Deploy** - Apply Kustomize staging overlay
4. **Smoke Test** - Health checks and API validation
5. **Notify** - Slack notification with status

### CD Production Pipeline

Manually triggered with optional image tag:

1. **Validate** - Verify image exists in ECR
2. **Deploy** - Apply Kustomize prod overlay (requires approval)
3. **Rollback** - Automatic rollback if deployment fails
4. **Validate** - Health checks and functional tests
5. **Release** - Create GitHub release tag
6. **Notify** - Slack notification

### Rollback Procedure

**Automatic (on failure)**
```yaml
- name: Rollback on failure
  if: failure() && steps.deploy.outcome == 'success'
  run: |
    kubectl rollout undo deployment/api -n legal-compliance
    kubectl rollout undo deployment/worker -n legal-compliance
```

**Manual Rollback**
```bash
# List recent deployments
kubectl rollout history deployment/api -n legal-compliance

# Rollback to previous
kubectl rollout undo deployment/api -n legal-compliance

# Rollback to specific revision
kubectl rollout undo deployment/api --to-revision=3 -n legal-compliance
```

### Security Scanning

Weekly security scan includes:

| Scan Type | Tool | Scope |
|-----------|------|-------|
| Python Dependencies | pip-audit | requirements.txt |
| Node Dependencies | npm audit | package.json |
| Python SAST | Bandit | backend/ |
| Multi-language SAST | Semgrep | Full repo |
| Secret Detection | Gitleaks | Git history |
| Container CVEs | Trivy | Docker images |
| IaC Security | Checkov | Dockerfile, K8s |

Results are uploaded to GitHub Security tab.

---

## Cost Estimate (EKS)

Understanding the cost breakdown helps with budgeting and identifying optimization opportunities:

| Service | Monthly | Notes |
|---------|---------|-------|
| EKS Control Plane | $73 | Fixed cost per cluster (consider multi-tenant for small workloads) |
| EC2 Nodes (3× t3.medium) | ~$90 | 2 vCPU, 4GB each; consider Reserved Instances for 30-60% savings |
| ALB | $20-30 | $0.0225/hour + $0.008/LCU-hour; shared across services |
| RDS PostgreSQL (×2) | $60-100 | db.t3.micro/small; app DB + Temporal DB |
| NAT Gateway | $30-45 | $0.045/hour + $0.045/GB; consider NAT instances for cost savings |
| ECR Storage | $5-10 | $0.10/GB-month; implement lifecycle policies to delete old images |
| CloudWatch Logs | $10-20 | $0.50/GB ingested; set retention policies (7-30 days typical) |
| **Total** | **~$290-370/mo** | Production baseline |

**Cost Optimization Strategies:**

| Strategy | Savings | Trade-off |
|----------|---------|-----------|
| **Reserved Instances (1yr)** | 30-40% on EC2 | Commitment; less flexibility |
| **Savings Plans** | 20-30% on compute | Requires usage analysis |
| **Spot Instances** | 60-90% on EC2 | Can be interrupted; use for workers |
| **Fargate Spot** | 70% on Fargate | Interruptible tasks only |
| **Right-sizing** | Variable | Monitor actual usage first |
| **NAT Instance** | 50-70% on NAT | Self-managed; less bandwidth |

**Dev Environment Cost:** ~$80-120/month (single replica, smaller instances, internal ALB)

---

## Key Kubernetes Best Practices Used

This deployment implements Kubernetes best practices across security, reliability, and operations:

### Security (Defense in Depth)

| Practice | Implementation | Why It Matters |
|----------|----------------|----------------|
| **Non-root containers** | `runAsUser: 1000`, `runAsNonRoot: true` | Limits blast radius of container escape vulnerabilities |
| **Read-only filesystem** | `readOnlyRootFilesystem: true` | Prevents attackers from modifying binaries or dropping malware |
| **No privilege escalation** | `allowPrivilegeEscalation: false` | Blocks sudo/setuid exploits |
| **IRSA for AWS access** | ServiceAccount annotations with IAM role ARN | No static credentials; temporary tokens via STS |
| **External Secrets** | Secrets synced from AWS Secrets Manager | No secrets in Git; centralized management with audit trail |
| **Network Policies** | Egress rules restrict outbound traffic | Pods can only reach RDS, Temporal - limits lateral movement |

### Reliability (High Availability)

| Practice | Implementation | Why It Matters |
|----------|----------------|----------------|
| **Multi-AZ spread** | `topologySpreadConstraints` with zone topology | Single AZ failure doesn't take down service |
| **Health probes** | Liveness (restart stuck pods) + Readiness (traffic routing) | Unhealthy pods automatically removed from rotation |
| **HPA autoscaling** | CPU/memory-based scaling 2-10 replicas | Handle traffic spikes without manual intervention |
| **Resource requests** | `requests.cpu`, `requests.memory` defined | Scheduler makes informed placement decisions |
| **Resource limits** | `limits.cpu`, `limits.memory` defined | Prevent runaway pods from affecting neighbors |
| **PodDisruptionBudget** | (Recommended to add) | Ensure minimum availability during node drains |

### Operations (GitOps & Observability)

| Practice | Implementation | Why It Matters |
|----------|----------------|----------------|
| **Kustomize overlays** | Base + dev/prod overlays | Environment parity; easy to audit differences |
| **Prometheus annotations** | `prometheus.io/scrape: "true"` on pods | Automatic metric discovery |
| **Structured logging** | JSON logs to stdout | CloudWatch/Datadog can parse and query |
| **Standard labels** | `app.kubernetes.io/*` labels | Consistent querying across tools |
| **Rolling updates** | Default deployment strategy | Zero-downtime deploys with gradual rollout |

---

## Quick Commands Reference

Common operations for managing the EKS deployment. Assumes `kubectl` is configured with the correct cluster context.

**Tip**: Use `kubectl config current-context` to verify you're targeting the right cluster before running commands.

### Deployment Commands

```bash
# Deploy to cluster (renders Kustomize and applies)
kubectl apply -k kube/overlays/prod

# Preview what will be applied (dry-run)
kubectl apply -k kube/overlays/prod --dry-run=client -o yaml

# Check deployment rollout status
kubectl rollout status deployment/api -n legal-compliance

# View deployment history
kubectl rollout history deployment/api -n legal-compliance
```

### Monitoring Commands

```bash
# Check pod status (include node placement)
kubectl get pods -n legal-compliance -o wide

# View logs (follow mode, last 100 lines)
kubectl logs -f deployment/api -n legal-compliance --tail=100

# View logs for a specific container in multi-container pod
kubectl logs deployment/api -n legal-compliance -c api

# Get pod events (useful for debugging scheduling issues)
kubectl describe pod -l app=api -n legal-compliance | grep -A 20 Events

# Check HPA status (current/target metrics)
kubectl get hpa -n legal-compliance
```

### Scaling Commands

```bash
# Manual scale (overrides HPA temporarily)
kubectl scale deployment api --replicas=5 -n legal-compliance

# Check current replica counts
kubectl get deployments -n legal-compliance

# Edit HPA limits (opens in editor)
kubectl edit hpa api-hpa -n legal-compliance
```

### Debugging Commands

```bash
# Port forward for local testing
kubectl port-forward svc/api 8000:8000 -n legal-compliance

# Execute command in running pod
kubectl exec -it deployment/api -n legal-compliance -- /bin/sh

# Check resource usage (requires metrics-server)
kubectl top pods -n legal-compliance

# Get all resources in namespace
kubectl get all -n legal-compliance
```

### Rollback Commands

```bash
# Rollback to previous deployment
kubectl rollout undo deployment/api -n legal-compliance

# Rollback to specific revision
kubectl rollout undo deployment/api --to-revision=3 -n legal-compliance

# Pause rollout (for canary-style deployments)
kubectl rollout pause deployment/api -n legal-compliance
kubectl rollout resume deployment/api -n legal-compliance
```

### Temporal Commands

```bash
# Install Temporal (first time)
helm repo add temporal https://charts.temporal.io
helm install temporal temporal/temporal -n temporal --create-namespace -f kube/temporal/values.yaml

# Upgrade Temporal
helm upgrade temporal temporal/temporal -n temporal -f kube/temporal/values.yaml

# Check Temporal pods
kubectl get pods -n temporal
```

### EKS-Specific Commands

```bash
# Update kubeconfig for EKS cluster
aws eks update-kubeconfig --name legal-compliance-eks --region us-east-1

# Check node status
kubectl get nodes -o wide

# Check AWS Load Balancer Controller logs
kubectl logs -n kube-system deployment/aws-load-balancer-controller

# Get ALB DNS name from Ingress
kubectl get ingress -n legal-compliance -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}'
```

---

## EKS Migration Checklist

Use this checklist when migrating from local Kubernetes (minikube, kind, Docker Desktop) to EKS:

### Pre-Migration (AWS Setup)

- [ ] Create EKS cluster via Terraform (see EKS Cluster Setup section)
- [ ] Configure VPC with public/private subnets across 3 AZs
- [ ] Create RDS PostgreSQL instances (app-db, temporal-db)
- [ ] Create secrets in AWS Secrets Manager
- [ ] Create ACM certificate for domain(s)
- [ ] Create ECR repositories for each Docker image
- [ ] Install AWS Load Balancer Controller in cluster
- [ ] Install External Secrets Operator in cluster
- [ ] Configure IRSA roles for service accounts

### Manifest Updates

- [ ] Update Ingress annotations with ACM certificate ARN
- [ ] Add IRSA annotations to ServiceAccount resources
- [ ] Create ClusterSecretStore for External Secrets
- [ ] Verify ExternalSecret resources reference correct AWS secrets
- [ ] Add health probes to worker deployment (if missing)
- [ ] Update image references to use ECR registry

### CI/CD Updates

- [ ] Add AWS credentials to GitHub Secrets
- [ ] Update CD workflows with EKS cluster name and region
- [ ] Configure ECR login in build workflows
- [ ] Test staging deployment pipeline

### Validation

- [ ] Deploy to dev/staging environment
- [ ] Verify ALB is created and DNS resolves
- [ ] Verify TLS certificate is working
- [ ] Verify pods can connect to RDS
- [ ] Verify External Secrets are synced
- [ ] Verify Temporal workers connect to Temporal server
- [ ] Run smoke tests against API endpoints
- [ ] Verify Prometheus metrics are scraped
- [ ] Verify CloudWatch logs are flowing

### Production Cutover

- [ ] Create DNS CNAME/alias to ALB
- [ ] Deploy to production with approval gate
- [ ] Monitor error rates and latency
- [ ] Verify HPA is scaling appropriately
- [ ] Document rollback procedure
- [ ] Update runbooks with EKS-specific commands

---

## References

- [EKS Best Practices Guide](https://aws.github.io/aws-eks-best-practices/)
- [Kustomize Documentation](https://kustomize.io/)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [External Secrets Operator](https://external-secrets.io/)
- [Temporal Helm Chart](https://github.com/temporalio/helm-charts)