# MasterBuilder7 Kubernetes Deployment Makefile

NAMESPACE := mb7
CONTEXT := $(shell kubectl config current-context)

.PHONY: help
help: ## Show this help message
	@echo "MasterBuilder7 Kubernetes Deployment"
	@echo "Current context: $(CONTEXT)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "\n\033[1m%-30s\033[0m %s\n", "Target", "Description"} /^[a-zA-Z_-]+:.*?##/ { printf "\033[36m%-30s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

.PHONY: deploy-all
deploy-all: ## Deploy all manifests
	kubectl apply -f .

.PHONY: deploy-base
deploy-base: ## Deploy namespace, configmaps, and secrets
	kubectl apply -f 01-namespace.yml
	kubectl apply -f 02-configmap.yml
	kubectl apply -f 03-secrets.yml

.PHONY: deploy-data
deploy-data: ## Deploy PostgreSQL and Redis
	kubectl apply -f 04-postgres-deployment.yml
	kubectl apply -f 05-redis-deployment.yml

.PHONY: deploy-app
deploy-app: ## Deploy MCP server and workers
	kubectl apply -f 06-mcp-server-deployment.yml
	kubectl apply -f 07-agent-worker-deployment.yml

.PHONY: deploy-monitoring
deploy-monitoring: ## Deploy Prometheus and Grafana
	kubectl apply -f 08-monitoring-deployment.yml

.PHONY: deploy-network
deploy-network: ## Deploy services and ingress
	kubectl apply -f 10-service.yml
	kubectl apply -f 09-ingress.yml

.PHONY: deploy-rbac
deploy-rbac: ## Deploy RBAC and HPA
	kubectl apply -f 11-hpa.yml
	kubectl apply -f 12-rbac.yml

.PHONY: delete-all
delete-all: ## Delete all resources
	@echo "WARNING: This will delete all resources in namespace $(NAMESPACE)"
	@read -p "Are you sure? [y/N] " confirm && [ $$confirm = y ] && kubectl delete namespace $(NAMESPACE) || echo "Cancelled"

.PHONY: status
status: ## Show status of all resources
	@echo "=== Pods ==="
	kubectl get pods -n $(NAMESPACE)
	@echo ""
	@echo "=== Services ==="
	kubectl get svc -n $(NAMESPACE)
	@echo ""
	@echo "=== Deployments ==="
	kubectl get deployments -n $(NAMESPACE)
	@echo ""
	@echo "=== HPA ==="
	kubectl get hpa -n $(NAMESPACE)

.PHONY: logs-api
logs-api: ## Show MCP server logs
	kubectl logs -l app.kubernetes.io/name=mcp-server -n $(NAMESPACE) --tail=100 -f

.PHONY: logs-worker
logs-worker: ## Show agent worker logs
	kubectl logs -l app.kubernetes.io/name=agent-worker -n $(NAMESPACE) --tail=100 -f

.PHONY: logs-postgres
logs-postgres: ## Show PostgreSQL logs
	kubectl logs -l app.kubernetes.io/name=postgres -n $(NAMESPACE) --tail=100 -f

.PHONY: logs-redis
logs-redis: ## Show Redis logs
	kubectl logs -l app.kubernetes.io/name=redis -n $(NAMESPACE) --tail=100 -f

.PHONY: port-forward-api
port-forward-api: ## Port forward MCP server to localhost:8000
	kubectl port-forward svc/mb7-mcp-server 8000:8000 -n $(NAMESPACE)

.PHONY: port-forward-grafana
port-forward-grafana: ## Port forward Grafana to localhost:3000
	kubectl port-forward svc/mb7-grafana 3000:3000 -n $(NAMESPACE)

.PHONY: port-forward-prometheus
port-forward-prometheus: ## Port forward Prometheus to localhost:9090
	kubectl port-forward svc/mb7-prometheus 9090:9090 -n $(NAMESPACE)

.PHONY: shell-api
shell-api: ## Open shell in MCP server pod
	kubectl exec -it deployment/mb7-mcp-server -n $(NAMESPACE) -- /bin/sh

.PHONY: shell-postgres
shell-postgres: ## Open shell in PostgreSQL pod
	kubectl exec -it statefulset/mb7-postgres -n $(NAMESPACE) -c postgres -- /bin/sh

.PHONY: shell-redis
shell-redis: ## Open shell in Redis pod
	kubectl exec -it statefulset/mb7-redis -n $(NAMESPACE) -c redis -- /bin/sh

.PHONY: db-migrate
db-migrate: ## Run database migrations
	kubectl exec -it deployment/mb7-mcp-server -n $(NAMESPACE) -- python -m alembic upgrade head

.PHONY: db-shell
db-shell: ## Open PostgreSQL shell
	kubectl run -it --rm psql --image=postgres:15 --restart=Never -n $(NAMESPACE) -- \
		psql postgresql://mb7_admin:$$(kubectl get secret mb7-secrets -n $(NAMESPACE) -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d)@mb7-postgres:5432/masterbuilder7

.PHONY: restart-api
restart-api: ## Restart MCP server deployment
	kubectl rollout restart deployment/mb7-mcp-server -n $(NAMESPACE)

.PHONY: restart-workers
restart-workers: ## Restart all worker deployments
	kubectl rollout restart deployment/mb7-agent-worker -n $(NAMESPACE)
	kubectl rollout restart deployment/mb7-build-worker -n $(NAMESPACE)
	kubectl rollout restart deployment/mb7-security-worker -n $(NAMESPACE)

.PHONY: rollout-status
rollout-status: ## Check rollout status
	kubectl rollout status deployment/mb7-mcp-server -n $(NAMESPACE)
	kubectl rollout status deployment/mb7-agent-worker -n $(NAMESPACE)
	kubectl rollout status deployment/mb7-build-worker -n $(NAMESPACE)

.PHONY: scale-api
scale-api: ## Scale MCP server (usage: make scale-api REPLICAS=5)
	kubectl scale deployment/mb7-mcp-server --replicas=$(REPLICAS) -n $(NAMESPACE)

.PHONY: scale-workers
scale-workers: ## Scale agent workers (usage: make scale-workers REPLICAS=10)
	kubectl scale deployment/mb7-agent-worker --replicas=$(REPLICAS) -n $(NAMESPACE)

.PHONY: test-endpoint
test-endpoint: ## Test API endpoint
	@curl -s http://localhost:8000/health | jq .

.PHONY: test-ingress
test-ingress: ## Test ingress endpoint (requires EXTERNAL_IP)
	@curl -s http://$(EXTERNAL_IP)/health | jq .

.PHONY: generate-secrets
generate-secrets: ## Generate random secrets
	@echo "Generating secrets..."
	@echo "POSTGRES_PASSWORD: $$(openssl rand -base64 32)"
	@echo "REDIS_PASSWORD: $$(openssl rand -base64 32)"
	@echo "JWT_SECRET: $$(openssl rand -base64 32)"
	@echo "ENCRYPTION_KEY: $$(openssl rand -base64 32)"

.PHONY: validate
validate: ## Validate manifests
	kubectl apply --dry-run=client -f .

.PHONY: verify
verify: ## Verify deployment is healthy
	@echo "=== Verifying deployment ==="
	@kubectl get pods -n $(NAMESPACE) -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\n"}{end}'
	@echo ""
	@echo "=== Service endpoints ==="
	@kubectl get endpoints -n $(NAMESPACE)
	@echo ""
	@echo "=== Ingress ==="
	@kubectl get ingress -n $(NAMESPACE)
