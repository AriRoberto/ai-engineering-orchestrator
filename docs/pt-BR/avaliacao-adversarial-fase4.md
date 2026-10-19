# Avaliação adversarial de evidências — Fase 4

Este documento registra o quarto incremento da Fase 4: uma suíte reproduzível para detectar
regressões nos controles aplicados ao conteúdo externo antes de habilitar um provedor real.

## Escopo

O corpus versionado em `evals/evidence-security.yaml` cobre:

- conteúdo benigno que deve continuar disponível;
- prompt injection direto em inglês e português;
- evasão por múltiplos espaços, quebra de linha e caracteres invisíveis;
- tentativa de redefinir a fronteira de mensagem de sistema;
- redaction de API keys, tokens GitHub e access keys AWS;
- validação automatizada de orçamento, SHA-256, origem e integridade das citações.

O guard normaliza Unicode com NFKC, remove caracteres invisíveis conhecidos e compacta whitespace
antes de aplicar os padrões. Isso reduz evasões simples sem interpretar nem executar o conteúdo.

## Execução

```bash
make eval-fase4
```

O comando executa o corpus no container do projeto, imprime um relatório JSON e retorna código
diferente de zero quando a taxa fica abaixo do limiar. O padrão é 100% para evitar que uma regressão
conhecida seja aceita silenciosamente.

## Resultado de referência

Execução em 15/10/2026:

| Categoria | Aprovados | Total |
|---|---:|---:|
| Conteúdo benigno | 2 | 2 |
| Prompt injection | 5 | 5 |
| Redaction de segredos | 3 | 3 |
| **Total** | **10** | **10** |

Taxa de aprovação: `1.0`. Limiar: `1.0`. Resultado: aprovado.

Além do corpus, os testes unitários adulteram citação, origem, hash e orçamento para confirmar que
o validador identifica cada violação. O laboratório real continua verificando as citações e fontes
persistidas do piloto público. Após o fortalecimento do guard, a execução conectada
`ba63671f-a46e-4481-92f0-b206cf569558` também foi concluída sem falso positivo no fluxo real.

## Limitações

Esta suíte demonstra comportamento apenas para os casos versionados. Expressões regulares não são
uma defesa completa contra prompt injection nem um detector completo de segredos. Novas evasões
descobertas devem primeiro entrar no corpus como caso reprodutível e depois orientar a correção.

O uso de um provedor real no piloto continua condicionado a avaliações adicionais de respostas
fundamentadas, ausência de vazamento e comportamento diante de entradas multilíngues mais amplas.
