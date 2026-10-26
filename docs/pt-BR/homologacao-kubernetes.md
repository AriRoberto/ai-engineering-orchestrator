# Homologação Kubernetes

O overlay `k8s/overlays/staging` prepara a aplicação para um cluster de homologação com imagem em
registry, banco persistente, entrada HTTPS e segredos sincronizados por um gerenciador externo. Ele
é neutro quanto ao provedor de nuvem; a plataforma fornece as implementações de storage,
`ClusterSecretStore`, Ingress e emissão de certificados.

## Pré-requisitos da plataforma

- cluster Kubernetes com uma `StorageClass` padrão e expansão/snapshot conforme a política local;
- NGINX Ingress Controller no namespace `ingress-nginx`;
- cert-manager e um `ClusterIssuer` chamado `letsencrypt-staging`;
- External Secrets Operator e um `ClusterSecretStore` chamado `staging-secret-store`;
- Prometheus e OpenTelemetry Collector opcionais no namespace `observability`, com os labels usados
  pelas políticas de rede;
- DNS controlado para o hostname real de homologação;
- acesso do pipeline ao GHCR e permissão de leitura da imagem pelo cluster.

O `ClusterSecretStore` é responsabilidade da plataforma e deve usar identidade de workload
federada para acessar AWS Secrets Manager, Google Secret Manager, Azure Key Vault ou serviço
equivalente. Não use access keys estáticas em manifests.

## Contrato de segredos

Cadastre estes valores no gerenciador externo:

| Chave remota | Conteúdo |
|---|---|
| `aieo/staging/runtime` | propriedade `database-url` com a URL PostgreSQL |
| `aieo/staging/api-keys` | documento JSON aceito por `AIEO_API_KEYS_FILE` |
| `aieo/staging/postgres` | propriedades `database`, `username` e `password` |
| `aieo/staging/registry` | propriedade `dockerconfigjson` com autenticação do registry |

O External Secrets Operator cria os objetos Kubernetes `orchestrator-runtime`,
`orchestrator-api-keys`, `postgres-credentials` e `orchestrator-registry`. Nenhum valor secreto é
versionado neste repositório.

## Preparar uma promoção

Valide primeiro o template:

```bash
make lab-homologacao
```

Publique a imagem no GHCR com uma tag vinculada ao commit e registre o digest retornado. Exemplo:

```bash
GIT_SHA="$(git rev-parse HEAD)"
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag "ghcr.io/ariroberto/ai-engineering-orchestrator:${GIT_SHA}" \
  --push .
```

O caminho oficial é o workflow **Publish container image**, que publica `linux/amd64` e
`linux/arm64`, gera SBOM, proveniência e atestação vinculada ao GitHub. Depois que o workflow estiver
na `main`, execute:

```bash
gh workflow run publish-image.yml -f tag="staging-$(git rev-parse --short=12 HEAD)"
gh run watch --workflow=publish-image.yml
```

Copie do resumo do workflow a referência `ghcr.io/...@sha256:...`. Não promova apenas pela tag. A
imagem atual da homologação foi publicada pela execução `40412874655` e está fixada em
`sha256:423c6262623e3940fe4fd3211586a03edd37777d4716c68b2ec1478a2942d19c`.

Os dois digests atuais já estão fixados e verificáveis. A aplicação usa
`sha256:423c6262623e3940fe4fd3211586a03edd37777d4716c68b2ec1478a2942d19c`; o
`pgvector/pgvector:pg17` usa o índice multi-arquitetura
`sha256:ac08538c6f8b9904c33c8224c5e5706dbe760aca29db1d096972b4052c22a75d`. Em uma promoção,
substitua o digest da aplicação pelo novo digest publicado pelo workflow. Substitua também
`orchestrator.staging.example.com` pelo hostname real e ajuste os nomes/labels de componentes da
plataforma quando forem diferentes.

Renderize e revise antes de aplicar:

```bash
.venv/bin/python scripts/renderizar-homologacao.py \
  --hostname orchestrator.staging.seu-dominio.example \
  --app-digest sha256:COLE-64-CARACTERES-HEXADECIMAIS \
  --secret-store NOME-DO-CLUSTER-SECRET-STORE \
  --cluster-issuer NOME-DO-CLUSTER-ISSUER \
  --storage-class NOME-DA-STORAGE-CLASS \
  --oidc-issuer https://seu-provedor-de-identidade.example/ \
  --oidc-audience ai-engineering-orchestrator \
  --oidc-jwks-url https://seu-provedor-de-identidade.example/.well-known/jwks.json \
  --output /tmp/aieo-staging.yaml
kubectl diff -f /tmp/aieo-staging.yaml
```

O renderizador trabalha em diretório temporário e não altera o overlay versionado. Para executar o
preflight contra um cluster externo antes de gerar o arquivo, acrescente:

```text
--context CONTEXTO-EXTERNO --check-cluster
```

O preflight rejeita kind, Docker Desktop e minikube; confirma os CRDs do External Secrets e
cert-manager, `ClusterSecretStore`, `ClusterIssuer`, IngressClass, StorageClass, resolução DNS e a
existência dos dois digests nos registries.

## Gate anterior à implantação externa

Não execute `kubectl apply` enquanto qualquer item abaixo estiver ausente:

- contexto de cluster externo dedicado à homologação;
- domínio real com DNS resolvendo para o Ingress;
- `ClusterSecretStore` com identidade federada e os quatro segredos do contrato;
- `ClusterIssuer` e IngressClass operacionais;
- StorageClass persistente com snapshot/restore testável;
- digest GHCR produzido pelo workflow e digest do PostgreSQL verificável;
- manifest renderizado pelo preflight sem placeholders;
- plano de rollback e janela de migração aprovados.

## Ordem de implantação

1. confirme `StorageClass`, Ingress, cert-manager, `ClusterIssuer` e External Secrets Operator;
2. confirme que os quatro `ExternalSecret` estão `Ready` e seus Secrets foram materializados;
3. aplique Service e StatefulSet do PostgreSQL e aguarde prontidão do banco;
4. execute o Job `orchestrator-migrations` e confirme `Complete`;
5. aplique o Deployment, Service, PDB, NetworkPolicies, Ingress e Certificate;
6. confirme rollout, `/health`, `/ready`, HTTPS, autenticação e métricas;
7. registre digest, revisão dos manifests, evidências e plano de rollback.

O PostgreSQL deste overlay usa um PVC de `20Gi` para homologação. Produção deve preferir serviço
gerenciado com alta disponibilidade, backup testado, restauração, criptografia e rotação próprias.
Uma implantação de homologação só é considerada validada após testar snapshot/restore e renovação
do certificado no cluster escolhido.

## Rollback

Reaplique o digest anterior da aplicação; nunca use uma tag mutável. Migrações devem permanecer
compatíveis com a versão anterior durante a janela de rollback. Não reverta ou apague o PVC como
parte do rollback da aplicação. Se uma migração não for retrocompatível, interrompa a promoção e
execute o runbook de banco aprovado pela equipe responsável.
