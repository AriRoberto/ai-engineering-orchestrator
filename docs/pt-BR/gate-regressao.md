# Gate unificado de regressão

O gate unificado executa os laboratórios do projeto em uma ordem conhecida e encerra os serviços
Compose ao terminar, inclusive quando uma etapa falha. Ele não substitui os testes unitários nem o
lint; consolida as validações reproduzíveis de integração e operação.

## Escopos

| Escopo | Comando | Validações |
|---|---|---|
| Estático | `make regressao-static` | Base Kubernetes, perfil de homologação e artefatos da release |
| Local | `make regressao` | Fases 2, 3, piloto público da Fase 4, observabilidade, acesso, Kubernetes, homologação e release |
| Completo | `make regressao-full` | Escopo local, piloto privado e cluster kind |

O escopo `local` é o padrão. Ele requer Docker, Docker Compose, `curl`, Python 3.12+, `kubectl` e acesso
de leitura ao repositório público do piloto. Não usa credenciais privadas.

O gate procura `.venv/bin/python`, `python3.12`, `python` e `python3`, nessa ordem. Use
`AIEO_PYTHON_BIN=/caminho/para/python3.12` quando o interpretador não estiver no `PATH` padrão.

O escopo `full` é deliberadamente explícito porque cria ou atualiza o cluster kind local e exige uma
credencial GitHub temporária, somente leitura e limitada ao repositório privado:

```bash
AIEO_GITHUB_PRIVATE_READ_TOKEN_FILE="$HOME/.config/aieo/github-app-ams-token" \
  make regressao-full
```

O gate nunca recebe o valor do token pela linha de comando. Ele encaminha somente o caminho do
arquivo já protegido aos laboratórios existentes.

## Uso no CI

O workflow executa `make regressao-static`, pois esse escopo não depende de serviços externos,
credenciais nem cluster persistente. A regressão `local` deve ser executada antes de promover uma
release; a regressão `full` registra a validação do ambiente local completo quando as credenciais e
ferramentas estiverem disponíveis.

Em caso de falha, a saída identifica a última etapa iniciada. Execute o laboratório indicado
isoladamente para obter o diagnóstico detalhado e consulte os logs com `make logs` quando a falha
envolver API ou PostgreSQL.

Em 26/10/2026, o escopo `local` concluiu inicialmente sete etapas em sequência. O gate passou a
incluir também a validação estática do perfil de homologação, totalizando oito etapas: fundação de
conhecimento e MCP, especialistas, evidências públicas, observabilidade, acesso governado,
manifests Kubernetes, perfil de homologação e artefatos da release. O encerramento automático
remove os serviços Compose ao final.
