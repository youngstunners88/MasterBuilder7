# MasterBuilder7 Kubernetes Deployment

Production-ready Kubernetes manifests for deploying MasterBuilder7 MCP Server on GKE, EKS, or AKS.

## 📁 Manifest Files

| File | Description |
|------|-------------|
| `01-namespace.yml` | Namespace, ResourceQuota, LimitRange |
| `02-configmap.yml` | Application, PostgreSQL, Redis, NGINX configurations |
| `03-secrets.yml` | Secrets for DB, Redis, API keys, TLS certificates |
| `04-postgres-deployment.yml` | PostgreSQL StatefulSet with persistent storage |
| `05-redis-deployment.yml` | Redis StatefulSet with persistence |
| `06-mcp-server-deployment.yml` | Main MCP API server deployment |
| `07-agent-worker-deployment.yml` | Agent, build, and security worker pools |
| `08-monitoring-deployment.yml` | Prometheus and Grafana deployments |
| `09-ingress.yml` | NGINX ingress with SSL/TLS |
| `10-service.yml` | ClusterIP services for all components |
| `11-hpa.yml` | Horizontal Pod Autoscalers (2-20 replicas) |
| `12-rbac.yml` | Service accounts, roles, and network policies |
| `kustomization.yml` | Kustomize configuration for easy customization |

## 🚀 Quick Start

### Prerequisites

- Kubernetes 1.24+
- kubectl configured
- Ingress controller (NGINX) installed
- cert-manager (optional, for TLS)

### Deploy All Components

```bash
# Using kubectl
kubectl apply -f MasterBuilder7/k8s/

# Using kustomize
kubectl apply -k MasterBuilder7/k8s/

# Verify deployment
kubectl get all -n mb7
```

### Deploy in Order (Recommended)

```bash
# 1. Create namespace and base resources
kubectl apply -f 01-namespace.yml
kubectl apply -f 02-configmap.yml

# 2. Create secrets (update with real values first!)
kubectl apply -f 03-secrets.yml

# 3. Deploy data stores
kubectl apply -f 04-postgres-deployment.yml
kubectl apply -f 05-redis-deployment.yml

# 4. Deploy application
kubectl apply -f 06-mcp-server-deployment.yml
kubectl apply -f 07-agent-worker-deployment.yml

# 5. Deploy monitoring
kubectl apply -f 08-monitoring-deployment.yml

# 6. Configure networking
kubectl apply -f 10-service.yml
kubectl apply -f 09-ingress.yml

# 7. Configure autoscaling and RBAC
kubectl apply -f 11-hpa.yml
kubectl apply -f 12-rbac.yml
```

## 🔐 Secrets Configuration

Update `03-secrets.yml` with actual values before deploying:

```bash
# Generate strong passwords
export POSTGRES_PASSWORD=$(openssl rand -base64 32)
export REDIS_PASSWORD=$(openssl rand -base64 32)
export JWT_SECRET=$(openssl rand -base64 32)

# Create secrets
kubectl create secret generic mb7-secrets \
  --from-literal=POSTGRES_USER=mb7_admin \
  --from-literal=POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  --from-literal=REDIS_PASSWORD="$REDIS_PASSWORD" \
  --from-literal=JWT_SECRET="$JWT_SECRET" \
  -n mb7

# Create TLS secret
kubectl create secret tls mb7-tls \
  --cert=path/to/cert.crt \
  --key=path/to/key.key \
  -n mb7
```

## 📊 Resource Configuration

### Default Resource Limits

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|--------------|
| MCP Server | 500m | 2000m | 512Mi | 2Gi |
| Agent Worker | 500m | 2000m | 1Gi | 4Gi |
| Build Worker | 1000m | 4000m | 2Gi | 8Gi |
| PostgreSQL | 500m | 2000m | 1Gi | 4Gi |
| Redis | 200m | 1000m | 512Mi | 2Gi |

### Horizontal Pod Autoscaling

| Component | Min | Max | Target CPU | Target Memory |
|-----------|-----|-----|------------|---------------|
| MCP Server | 2 | 20 | 70% | 80% |
| Agent Worker | 2 | 20 | 75% | 80% |
| Build Worker | 2 | 20 | 70% | 75% |
| Security Worker | 2 | 10 | 80% | - |

## 🌐 Ingress Configuration

Update `09-ingress.yml` with your domains:

```yaml
spec:
  tls:
  - hosts:
    - api.yourdomain.com
    secretName: mb7-tls
  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        backend:
          service:
            name: mb7-mcp-server
            port:
              number: 8000
```

## 📈 Monitoring

### Access Prometheus
```bash
kubectl port-forward svc/mb7-prometheus 9090:9090 -n mb7
# Open http://localhost:9090
```

### Access Grafana
```bash
kubectl port-forward svc/mb7-grafana 3000:3000 -n mb7
# Open http://localhost:3000
# Default credentials: admin/admin (change in production!)
```

## 🔧 Cloud Provider Specific Notes

### Google Kubernetes Engine (GKE)

```bash
# Create GKE cluster
gcloud container clusters create mb7-cluster \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type e2-standard-4 \
  --enable-autoscaling \
  --min-nodes 3 \
  --max-nodes 20 \
  --enable-autorepair \
  --enable-autoupgrade

# Get credentials
gcloud container clusters get-credentials mb7-cluster --zone us-central1-a

# Install NGINX ingress
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml

# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

### Amazon Elastic Kubernetes Service (EKS)

```bash
# Create EKS cluster
eksctl create cluster \
  --name mb7-cluster \
  --region us-west-2 \
  --node-type m5.xlarge \
  --nodes 3 \
  --nodes-min 3 \
  --nodes-max 20 \
  --managed

# Update storage class for AWS
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: mb7-postgres-storage
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
EOF
```

### Azure Kubernetes Service (AKS)

```bash
# Create AKS cluster
az aks create \
  --resource-group mb7-rg \
  --name mb7-cluster \
  --node-count 3 \
  --enable-cluster-autoscaler \
  --min-count 3 \
  --max-count 20 \
  --node-vm-size Standard_D4s_v3

# Get credentials
az aks get-credentials --resource-group mb7-rg --name mb7-cluster

# Update storage class for Azure
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: mb7-postgres-storage
provisioner: disk.csi.azure.com
parameters:
  skuName: Premium_LRS
  cachingMode: ReadOnly
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
EOF
```

## 🔒 Security

### Network Policies

The deployment includes restrictive network policies:
- Default deny all ingress/egress
- Explicit allow rules for required communication
- Database access restricted to app components only

### RBAC

- Service accounts with minimal required permissions
- Role-based access control for each component
- Pod Security Standards (restricted profile)

### Pod Security

- Non-root containers
- Read-only root filesystem where possible
- Dropped capabilities
- Seccomp profiles enabled

## 🧪 Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n mb7
kubectl describe pod <pod-name> -n mb7
kubectl logs <pod-name> -n mb7 --tail 100
```

### Check Services
```bash
kubectl get svc -n mb7
kubectl get endpoints -n mb7
```

### Check Ingress
```bash
kubectl get ingress -n mb7
kubectl describe ingress mb7-ingress -n mb7
```

### Debug HPA
```bash
kubectl get hpa -n mb7
kubectl describe hpa mb7-mcp-server-hpa -n mb7
```

### Database Connection Issues
```bash
# Test DB connection from a pod
kubectl run -it --rm debug --image=postgres:15 --restart=Never -n mb7 -- \
  psql postgresql://mb7_admin:password@mb7-postgres:5432/masterbuilder7
```

## 📚 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [cert-manager Documentation](https://cert-manager.io/docs/)
- [Prometheus Operator](https://github.com/prometheus-operator/prometheus-operator)

## 📄 License

Copyright (c) 2026 MasterBuilder7. All rights reserved.
