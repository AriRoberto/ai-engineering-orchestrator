# Laboratório prático — Fase 2

Este laboratório executa uma demonstração local, gratuita e reproduzível. Todos os dados são
fictícios, o provedor de LLM é simulado e nenhuma credencial corporativa é necessária.

## Objetivos

Ao final, você terá validado:

- API e PostgreSQL com pgvector;
- ingestão e fragmentação de um documento;
- busca híbrida e isolamento entre projetos;
- recuperação de conhecimento dentro de uma execução;
- consolidação simulada e contabilização estimada de tokens;
- bloqueio de um padrão de prompt injection;
- registro de feedback humano.

## Execução rápida no MacBook Apple Silicon

Na raiz do repositório e na branch `develop`:

```bash
cp .env.example .env
make verificar
make lab-fase2
```

O script constrói as imagens, inicia os containers e executa sete verificações. Ao final, deve
mostrar `Laboratório concluído com sucesso`, o UUID da execução e o endereço do Swagger.

## Inspeção manual

Abra:

- Swagger: http://localhost:8000/docs
- Health check: http://localhost:8000/health

Consulte os logs:

```bash
make logs
```

Procure o evento estruturado `execution_processed`, o UUID apresentado pelo laboratório e o estado
`COMPLETED`.

## Encerramento

```bash
make compose-down
```

Esse comando preserva o volume do PostgreSQL. Para reiniciar os dados exclusivamente deste ambiente
de demonstração, execute conscientemente `docker compose down -v`; essa opção apaga o volume local.

## Problemas comuns

### Docker Desktop não está aberto

Abra o Docker Desktop, aguarde o mecanismo iniciar e execute novamente `make verificar`.

### Porta 8000 ocupada

Encerre o processo que utiliza a porta ou defina outro mapeamento temporário no `compose.yaml`.

### Documento já existente

Documentos repetidos são permitidos na fundação atual. Eles podem produzir mais de um resultado na
busca, sem invalidar o laboratório.

### API não ficou pronta

Execute `make logs`. Verifique principalmente os serviços `api` e `postgres` e confirme que o banco
atingiu o estado `healthy`.
