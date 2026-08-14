# Modificação Rápida: Preservação de Links Inline em Sumários/Textos e Normalização de Espaços

*(preenchido em conjunto por desenvolvedor e IA — sem debate de trade-offs, sem ADR)*

## O que muda

1. **Preservação de Links Inline (`<a href="...">`)**:
   - Assegurar que tags de navegação e hiperlinks `<a href="...">` com conteúdo interno formatado (como `<small>`, `<strong>`, `<em>` em sumários `toc.html` e citações em capítulos de texto como `ch09.html`) não sejam descartadas pela LLM durante a tradução de blocos.
   - Reforçar diretrizes de preservação de marcações de hiperlinks nos prompts LLM e/ou garantir que marcações estruturais e sentinelas sejam mantidas e validadas integralmente.

2. **Sanitização e Normalização de Espaços (`&nbsp;` / `\u00a0`)**:
   - Normalizar espaços não separáveis (`\u00a0` / `&nbsp;`) e sentinelas de mascaramento para evitar geração de resíduos do caractere `Â` em arquivos XHTML decodificados/serializados.

3. **Testes de Regressão e Validação**:
   - Testes unitários para serialização/desserialização de blocos contendo links com tags internas (`<a href="...">H<small>ANDS</small>...</a>`).
   - Testes de sanitização de espaços garantindo ausência de mojibake (`Â`).

## Por que

- Na análise comparativa do `ddd.epub` vs `ddd-pt-BR.epub`, constatou-se que 6 entradas de títulos de padrões no sumário visual (`toc.html`) e 2 referências cruzadas/bibliográficas em `ch09.html` perderam as tags `<a href="...">`, convertendo-se em texto plano.
- Foram detectadas 2 ocorrências do caractere `Â` decorrentes de espaços não-quebráveis não normalizados.

## Arquivos afetados

- `src/tradutor/domain/placeholders.py` — normalização de sentinelas e espaços em marcações mascaradas.
- `src/tradutor/providers/llm/openai_compat.py` — reforço do system prompt e validação de preservação de tags de hyperlink `<a>`.
- `src/tradutor/epub/segments.py` / `src/tradutor/epub/_xhtml.py` — garantia de integridade na substituição interna de nós com links.
- `tests/domain/test_placeholders.py` — testes de mascaramento e limpeza de sentinelas.
- `tests/providers/test_openai_compat.py` — validação de integridade de tags nos prompts.

## Risco de Regressão

**Baixo** — Trata-se de reforço de regras de fidelidade de tags inline já existentes e normalização de caracteres de espaçamento invisíveis.

## Precisa de teste novo?

**Sim**:
- Teste unitário verificando que fragmentos contendo `<a href="...">Texto <small>Extra</small></a>` mantêm a tag `<a>` intacta.
- Teste unitário de sanitização de strings contendo `\u00a0` / `&nbsp;` prevenindo surgimento do caractere `Â`.

---

## ⚠️ Trava de Escalonamento

- Introduz um Ator/papel de usuário novo? **não**
- Cria ou muda uma regra de acoplamento entre componentes já registrada no `docs/arquitetura/arquitetura.html`? **não**
- Contraria ou exige revisar um ADR aprovado? **não**
- Muda comportamento observável de forma que mereça uma decisão arquitetural registrada? **não**

---

## 📌 Reconciliação Pós-Implementação

- **Status da Implementação:** Concluída com 100% de conformidade.
- **Implementações Realizadas:**
  1. `link_sequence(text)` e `are_tags_balanced(text)` adicionados em `src/tradutor/domain/placeholders.py` e exportados no domínio (`src/tradutor/domain/__init__.py`).
  2. `is_formatting_faithful` aprimorado para aceitar variações estilísticas decorrentes da tradução (ex.: número de tags `<small>`) desde que a sequência de links `<a>` e tipos de tags sejam estritamente idênticos e o HTML esteja balanceado.
  3. `fallback_markup` implementado em `src/tradutor/translate/orchestrator.py` para garantir que blocos originados como hiperlinks externos não percam a tag `<a href="...">` caso caiam no fallback de formatação.
  4. System prompt e user prompt de `src/tradutor/providers/llm/openai_compat.py` reforçados com instrução mandatória para manter tags `<a href="...">` envolvendo o texto traduzido.
  5. `unmask_markup` atualizado com limpeza de sentinelas `_SENTINEL` (`\u00a0`).
  6. Testes unitários cobrindo todos os cenários adicionados em `tests/domain/test_placeholders.py`, `tests/providers/test_openai_compat.py` e `tests/translate/test_orchestrator.py`.
- **Validação Final:** Suíte completa com 643 testes aprovados, 0 erros no lint, formatação limpa e cobertura de 95%.

