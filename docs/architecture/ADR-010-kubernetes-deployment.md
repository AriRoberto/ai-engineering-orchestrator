# ADR-010 — Implantação Kubernetes segura

## Contexto

A Fase 5 precisa transformar a imagem local em uma unidade implantável sem incorporar credenciais,
conceder acesso desnecessário à API do cluster ou confundir processo vivo com serviço pronto.

## Decisão

Adotar uma base Kustomize independente de provedor com duas réplicas, ServiceAccount sem token
automático, Pod Security `restricted`, filesystem somente leitura, capacidades removidas, recursos,
probes de inicialização, vida e prontidão, PDB e NetworkPolicy. A prontidão consulta o PostgreSQL;
a vida verifica somente o processo. Segredos são fornecidos externamente por referências.

As migrações idempotentes são executadas por um Job explícito usando a mesma imagem da aplicação.
Ingress, TLS, identidade federada, armazenamento do PostgreSQL e destinos exatos de rede pertencem
a overlays específicos da plataforma.

## Consequências

- os manifests são renderizáveis e verificáveis sem cluster;
- nenhuma credencial ou objeto `Secret` é versionado;
- indisponibilidade do banco remove pods do balanceamento sem reiniciar processos saudáveis;
- a imagem deve conter as migrações e ser fixada por digest em cada ambiente;
- a NetworkPolicy base precisa ser estreitada conforme DNS, banco, coleta e egress do cluster real.
