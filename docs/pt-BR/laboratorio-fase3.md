# Laboratório prático — Fase 3

Este laboratório demonstra os agentes de Banco de Dados, QA, Segurança e Documentação sem acessar
projetos externos ou usar credenciais.

## Execução

Na raiz do repositório:

```bash
make verificar
make lab-fase3
```

O script executa cinco verificações:

1. inicia a aplicação completa;
2. aguarda o health check;
3. confirma o catálogo com oito especialistas;
4. executa os quatro agentes da Fase 3 sobre evidências fictícias;
5. consulta a execução persistida e confirma o isolamento entre projetos.

Ao final, o terminal apresenta o UUID da execução e o endereço do Swagger. Os containers continuam
ativos para inspeção; encerre-os com `make compose-down`.

## Resultado esperado

A execução deve terminar em `COMPLETED`, com exatamente quatro resultados: `database`, `qa`,
`security` e `documentation`. Cada resultado deve conter pelo menos dois achados e as evidências
compatíveis com sua responsabilidade.

O campo `simulated` permanece `true`: o laboratório valida contratos, roteamento e governança, não
alega uma análise real de repositório.
