# Implantação Kubernetes

O diretório `base` contém uma base Kustomize para a API e pressupõe PostgreSQL/pgvector externo.
Nenhum segredo é versionado. Antes da aplicação, crie no namespace os segredos esperados:

```bash
kubectl create namespace ai-engineering-orchestrator --dry-run=client -o yaml | kubectl apply -f -
kubectl -n ai-engineering-orchestrator create secret generic orchestrator-runtime \
  --from-literal=database-url='postgresql+psycopg://USER:PASSWORD@HOST:5432/DB'
kubectl -n ai-engineering-orchestrator create secret generic orchestrator-api-keys \
  --from-file=api-keys.json=/caminho/seguro/api-keys.json
```

Fixe a imagem por digest no overlay do ambiente, execute primeiro o Job de migração e então aplique
o Deployment. Para inspecionar ou validar localmente:

```bash
kubectl kustomize k8s/base
make lab-fase5-kubernetes
```

A base não publica Ingress: TLS, hostname, autenticação federada e regras de entrada dependem da
plataforma. A `NetworkPolicy` permite tráfego de entrada apenas dentro do namespace e saída DNS,
PostgreSQL e HTTPS; ajuste os seletores e destinos no overlay do cluster.
