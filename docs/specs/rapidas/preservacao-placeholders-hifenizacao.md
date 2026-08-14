# Modificação Rápida: Normalização de placeholders em palavras hifenizadas e reforço de prompt LLM

*(preenchido em conjunto por desenvolvedor e IA — sem debate de trade-offs, sem ADR)*

## O que muda
1. Normalizar templates de extração de conteúdo protegido em `src/tradutor/domain/placeholders.py` quando um placeholder determinístico `{{N}}` ou token estiver embutido no meio de palavra com hífen (`word-{{0}}rest` $\to$ `wordrest {{0}}`), permitindo que a LLM processe o vocábulo íntegro e preserve o placeholder adjacente.
2. Reforçar o system prompt em `src/tradutor/providers/llm/openai_compat.py` com regra explícita proibindo omissão, remoção ou modificação de tokens e placeholders numéricos.
3. Testes unitários cobrindo extração e restauração de palavras hifenizadas e validação de prompts.

## Por que
- Em livros digitalizados (como `ddd.epub`), quebras de linha com hifenização tipográfica frequentemente contêm âncoras vazias de página no meio de palavras (ex.: `every-<a id="page_419"></a>one`).
- Ao extrair `every-{{0}}one`, a LLM traduz "everyone" para "todos" em português e descarta o token `{{0}}`, fazendo o verificador estrito de integridade `is_faithful` reprovar o bloco no controle de qualidade e travar a conclusão do livro aos 99.98%.

## Arquivos afetados
- `src/tradutor/domain/placeholders.py` — normalização de hifenização na extração de placeholders.
- `src/tradutor/providers/llm/openai_compat.py` — reforço do system prompt de tradução.
- `tests/domain/test_placeholders.py` — testes de extração/restauração com âncoras hifenizadas.
- `tests/providers/test_openai_compat.py` — validação do novo prompt.

## Risco de Regressão
Baixo — a normalização apenas unifica fragmentos de palavras separadas por hífen tipográfico em torno de âncoras/tags inline e move o token para o lado, preservando a capacidade de restauração com `restore_protected`.

## Precisa de teste novo?
Sim:
- Teste unitário de `extract_protected` e `restore_protected` com `every-<a id="..."></a>one` garantindo que o template vire `everyone {{0}}` e restaure `<a id="..."></a>`.
- Teste de system prompt em `test_openai_compat.py` validando as novas diretrizes.

---

## ⚠️ Trava de Escalonamento

- Introduz um Ator/papel de usuário novo? **não**
- Cria ou muda uma regra de acoplamento entre componentes já registrada no `arquitetura.html`? **não**
- Contraria ou exige revisar um ADR aprovado? **não**
- Muda comportamento observável de forma que mereça uma decisão arquitetural registrada? **não**
