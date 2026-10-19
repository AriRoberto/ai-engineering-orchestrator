# Fase 3 — Especialização dos diagnósticos

O primeiro incremento da Fase 3 amplia o catálogo de quatro para oito agentes. Os novos
especialistas seguem o mesmo contrato estruturado, recebem somente a solicitação e as evidências
declaradas e não executam comandos no host.

## Agentes entregues

### Banco de Dados

Identifica arquivos SQL, schemas e diretórios de migrações. Informa quantas evidências foram
fornecidas e se há sinal de migrações versionadas. Não conecta em bancos nem executa SQL.

### QA

Identifica arquivos de teste e os correlaciona com workflows de CI. O diagnóstico distingue a
existência de testes da evidência de execução automatizada.

### Segurança

Identifica documentos e arquivos associados a controles, além de nomes que podem representar
material sensível, como `.env`, `id_rsa` e `secrets.yaml`. O agente sinaliza revisão; não lê nem
expõe o conteúdo desses arquivos.

### Documentação

Inventaria Markdown e verifica a presença das referências mínimas `README.md`, `CHANGELOG.md` e
`SECURITY.md`, apoiando a rastreabilidade que será usada na futura documentação oficial.

## Roteamento

O roteamento permanece determinístico. Termos relacionados a banco de dados, QA, segurança e
documentação selecionam os respectivos agentes. Uma solicitação pode selecionar vários
especialistas, e o limite padrão de etapas passou de 8 para 12 para comportar o catálogo completo e
a etapa opcional de recuperação de conhecimento.

## Contratos e limites

- cada resultado contém `agent`, `summary`, `findings`, `evidence` e `simulated`;
- arquivos repetidos são removidos preservando a ordem;
- os diagnósticos se limitam aos nomes e metadados fornecidos em `context.files`;
- ausência de evidência é reportada explicitamente;
- nenhuma conclusão é apresentada como varredura real de código, banco ou infraestrutura.

## Validação

Execute:

```bash
make lab-fase3
```

O laboratório confirma os oito agentes, executa os quatro novos especialistas em conjunto, valida
achados estruturados e comprova persistência e isolamento da execução.

## Próximo incremento

A especialização seguinte deve introduzir coleta controlada de evidências reais em repositórios
piloto somente leitura. Isso exige autenticação, escopo explícito, proveniência dos arquivos e
limites de tamanho antes de substituir as evidências declaradas pelo cliente.
