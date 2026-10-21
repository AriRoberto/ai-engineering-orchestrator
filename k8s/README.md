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

## Cluster local reproduzível

O overlay `k8s/overlays/local` cria um ambiente isolado para validação sem homologação externa. Ele
inclui PostgreSQL/pgvector efêmero, API, Job de migração, autenticação, probes, políticas de rede e
imagem carregada diretamente no kind. Pré-requisitos: Docker Desktop, `kind`, `kubectl`, `curl` e
`openssl`.

```bash
make lab-kubernetes-local
```

O laboratório cria ou reutiliza o cluster `aieo-local`, executa os pilotos, testa rollout e
rollback e mantém o ambiente ativo. Uma API key é gerada em `~/.config/aieo/local-api-key`, com
permissão `600`; nenhum valor entra no Git ou é impresso. Para acessar a API:

```bash
kubectl --context kind-aieo-local -n ai-engineering-orchestrator \
  port-forward service/orchestrator-api 18080:80
```

Em outro terminal:

```bash
curl http://127.0.0.1:18080/ready
curl -H "X-API-Key: $(< ~/.config/aieo/local-api-key)" \
  http://127.0.0.1:18080/v1/agents
```

Se `AIEO_GITHUB_PRIVATE_READ_TOKEN_FILE` apontar para um token válido, o laboratório monta o secret,
valida `app-ams`, apaga o secret do Kubernetes e reinicia a API sem ele. Para remover todo o
ambiente, inclusive a API key local:

```bash
make lab-kubernetes-local-down
```

O banco usa `emptyDir` deliberadamente: cada execução recria o StatefulSet e valida as migrações a
partir de uma instância limpa. Persistência, Ingress, TLS e secret manager permanecem decisões do
ambiente de homologação ou produção.
