# Release 0.2.0 — checklist de promoção

Publicada em 20/10/2026. Origem: `develop`. Destino: `main`. Tag: `v0.2.0`.

## Gate obrigatório

- [x] versão consistente na API, pacote Python, UI e manifests;
- [x] lint e suíte automatizada aprovados;
- [x] build da imagem e UI aprovado;
- [x] laboratórios públicos das fases 2 a 5 preservados;
- [x] regras Prometheus, dashboard e Kustomize validados;
- [x] documentação oficial, segurança, arquitetura, ADRs e CHANGELOG atualizados;
- [x] limitações externas declaradas;
- [x] CI do PR de promoção para `main` aprovado;
- [x] promoção autorizada conforme a proteção da `main`;
- [x] tag `v0.2.0` criada depois do merge.

## Evidências atuais

- 78 testes automatizados e 91% de cobertura no incremento 7;
- 11 regras Prometheus aprovadas pelo `promtool`;
- laboratório Prometheus/Grafana e laboratório Kubernetes aprovados;
- incrementos revisados individualmente nos PRs #1 a #15.
- promoção concluída pelo PR #18 no commit `b63311d`.

## Pendências que não bloqueiam esta release local

Validação do piloto privado, implantação em cluster, retenção de 30 dias, identidade federada,
quota distribuída e canal gerenciado de notificação dependem de ambientes ou credenciais externos.
Esses itens permanecem no plano e não devem ser marcados como concluídos durante a promoção.
