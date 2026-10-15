# Laboratório prático — piloto público da Fase 4

Este laboratório consulta a árvore pública real de `AriRoberto/app-financas`. Ele requer acesso à
internet, mas não exige token do GitHub e não modifica o repositório piloto.

## Execução

```bash
make verificar
make lab-fase4
```

O laboratório inicia a aplicação, solicita uma execução com `include_content=true` e valida:

- provedor `github` e modo somente leitura;
- revisão Git com SHA identificável;
- arquivos com caminho, SHA, tamanho e URL de origem;
- exclusão de dependências vendorizadas do orçamento de evidências;
- pelo menos um conteúdo aprovado ou redacted com SHA-256;
- ausência de texto persistido em qualquer item em quarentena;
- conclusão e persistência da execução;
- negação do projeto privado `app-ams`.

Falhas de DNS, rate limit ou indisponibilidade do GitHub encerram a execução sem usar dados parciais.
