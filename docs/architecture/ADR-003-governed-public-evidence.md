# ADR-003: Coleta governada de evidências públicas

- Status: aceito; estendido pelo ADR-004
- Data: 15/10/2026

## Contexto

Os agentes especializados recebiam nomes de arquivos declarados pelo cliente. Para iniciar os
pilotos reais sem ampliar prematuramente privilégios, o sistema precisa coletar evidências de um
repositório público conhecido, preservando proveniência e limites verificáveis.

## Decisão

O backend constrói o destino exclusivamente a partir do YAML de projeto. O cliente informa apenas
o `project_id`; URLs arbitrárias não são aceitas. A coleta inicial usa a API de árvores Git do
GitHub, somente para projetos `public` e `read-only`.

São coletados metadados de blobs relevantes — caminho, SHA, tamanho e URL de origem — sem baixar ou
executar conteúdo. Árvores truncadas são recusadas. Quantidade de arquivos, tamanho individual e
tamanho total possuem limites configuráveis. A revisão da árvore é anexada ao contexto e persistida
com a execução.

## Consequências

- o piloto `app-financas` pode gerar diagnósticos reproduzíveis sobre um inventário real;
- o piloto privado `app-ams` permanece negado sem autenticação de leitura;
- SSRF é reduzido pela origem fixa `https://api.github.com` e pelo repositório vindo da configuração;
- análises continuam limitadas a metadados; conteúdo, diffs e histórico não são coletados;
- indisponibilidade, rate limit ou resposta truncada do GitHub fazem a operação falhar fechada.

## Referências

- [Git Trees API](https://docs.github.com/en/rest/git/trees?apiVersion=2022-11-28)
- [Repository contents API](https://docs.github.com/pt/rest/repos/contents?apiVersion=2022-11-28)
- [ADR-004 — conteúdo textual controlado](ADR-004-controlled-text-evidence.md)
