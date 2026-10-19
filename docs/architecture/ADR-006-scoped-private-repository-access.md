# ADR-006: Acesso autenticado e escopado a repositório privado

- Status: aceito para o quinto incremento da Fase 4
- Data: 16/10/2026

## Contexto

O piloto `app-ams` é privado e não pode ser analisado pelo transporte público. A credencial não pode
ser aceita na API, persistida na execução, incorporada ao contexto dos agentes ou compartilhada com
o provedor de LLM. O acesso deve continuar limitado a leitura e ao repositório configurado.

## Decisão

O transporte GitHub recebe um `GitHubCredentialProvider`. O provedor somente entrega credencial
quando `owner/repository` coincide exatamente com o escopo configurado. Projetos privados também
precisam declarar `authenticated_read_only: true`; modos de escrita continuam recusados.

Em Compose, a opção recomendada monta o token como secret em arquivo. O provedor lê no máximo 4 KB
por solicitação, não mantém o valor em representação textual e falha fechado quando o arquivo está
ausente, ilegível, vazio ou excede o limite. O cabeçalho `Authorization` é criado apenas dentro do
transporte e somente para o repositório permitido.

O primeiro laboratório privado coleta apenas metadados (`include_content=false`). A resposta
registra visibilidade privada e uso de autenticação, mas não contém token, cabeçalho ou referência
ao secret. Sem credencial, a API retorna HTTP 403 antes de consultar o GitHub. Todas as tentativas
são registradas em `evidence_access_audits` como `COMPLETED`, `DENIED` ou `FAILED`, isoladas por
projeto e sem material de autenticação.

## Consequências

- o mesmo pipeline de proveniência pode atender repositórios públicos e privados;
- uma credencial comprometida continua limitada pelas permissões configuradas no GitHub;
- o secret não entra no domínio, banco, logs estruturados ou payload HTTP;
- rotação e expiração pertencem ao emissor/secret store, sem reiniciar o desenho do domínio;
- a validação real depende de uma credencial externa de escopo mínimo e não é simulada como sucesso.

## Referências

- [ADR-003 — coleta governada de evidências públicas](ADR-003-governed-public-evidence.md)
- [Laboratório privado da Fase 4](../pt-BR/laboratorio-fase4-privado.md)
- [REST API authentication](https://docs.github.com/en/rest/authentication/authenticating-to-the-rest-api)
- [Managing fine-grained personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
