# ADR-012 — Perfil de plataforma para homologação

## Contexto

A base Kubernetes e o overlay local validam a aplicação, mas não cobrem distribuição por registry,
persistência, exposição TLS ou sincronização de segredos. Esses controles dependem do cluster e não
devem introduzir credenciais, nomes de conta ou dependência rígida de um provedor na base.

## Decisão

Adotar um overlay Kustomize de homologação com:

- imagem no GHCR fixada por digest, com placeholder inválido que falha de forma segura;
- PostgreSQL/pgvector em StatefulSet com PVC para homologação;
- Ingress NGINX e Certificate emitido pelo cert-manager;
- External Secrets Operator referenciando um `ClusterSecretStore` fornecido pela plataforma;
- políticas de rede explícitas para Ingress, Prometheus, PostgreSQL, OTLP, DNS e HTTPS;
- identidade federada configurada no `ClusterSecretStore`, nunca credenciais estáticas no Git.

O perfil permanece neutro de nuvem. Hostname, digest, StorageClass e objetos globais de plataforma
são parâmetros obrigatórios da promoção. Produção deve substituir o PostgreSQL interno por serviço
gerenciado e demonstrar backup/restauração antes de receber tráfego.

## Consequências

- o repositório passa a ter um contrato verificável para homologação sem armazenar Secrets;
- o template não pode ser aplicado acidentalmente antes da substituição do digest e hostname;
- CRDs e controladores de Ingress, cert-manager e External Secrets tornam-se pré-requisitos;
- a implantação real depende da preparação do cluster e da validação externa correspondente;
- persistência local no cluster é adequada apenas para homologação e não implica prontidão de
  produção.
