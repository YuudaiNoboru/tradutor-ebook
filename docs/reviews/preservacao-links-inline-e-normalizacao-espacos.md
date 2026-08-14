# Relatório de Review: Preservação de Links Inline em Sumários/Textos e Normalização de Espaços

*(preenchido pela IA — referência: `docs/specs/rapidas/preservacao-links-inline-e-normalizacao-espacos.md` e `docs/arquitetura/arquitetura.html`)*

---

## 1. Escopo Revisado

- **Identificador da mudança:** `preservacao-links-inline-e-normalizacao-espacos`
- **Spec de referência:** `docs/specs/rapidas/preservacao-links-inline-e-normalizacao-espacos.md`
- **Arquivos tocados no diff:**
  - `src/tradutor/domain/__init__.py`
  - `src/tradutor/domain/placeholders.py`
  - `src/tradutor/providers/llm/openai_compat.py`
  - `src/tradutor/translate/__init__.py`
  - `src/tradutor/translate/orchestrator.py`
  - `tests/domain/test_placeholders.py`
  - `tests/providers/test_openai_compat.py`
  - `tests/translate/test_orchestrator.py`

---

## 2. 🔴 Bloqueadores

Nenhum bloqueador encontrado.

---

## 3. 🟡 Atenção

Nenhum ponto de atenção encontrado.

---

## 4. 🔵 Sugestões

- **[src/tradutor/domain/placeholders.py:170]** O conjunto `_INLINE_OPEN_CLOSE_TAGS` cobre as tags inline estilísticas comuns do padrão EPUB/XHTML (como `small`, `em`, `strong`, `b`, `i`, `span`, `a`, `sub`, `sup`, `code`, `cite`, `u`, `s`), garantindo validação de balanceamento robusta e segura.

---

## 5. Checklist de Fitness Functions (da spec)

N/A — modificação rápida, sem checklist de Fitness Functions.
- **Precisa de teste novo?** Sim:
  - `test_link_sequence_extracts_and_normalizes_anchor_tags` implementado em `tests/domain/test_placeholders.py`.
  - `test_are_tags_balanced_detects_valid_and_broken_nesting` implementado em `tests/domain/test_placeholders.py`.
  - `test_is_formatting_faithful_accepts_style_count_variation_with_preserved_links` implementado em `tests/domain/test_placeholders.py`.
  - `test_unmask_markup_strips_sentinel_even_if_not_in_empty` implementado em `tests/domain/test_placeholders.py`.
  - `test_fallback_markup_preserves_outer_anchor` implementado em `tests/translate/test_orchestrator.py`.
  - Testes de validação de prompt de hyperlinks atualizados em `tests/providers/test_openai_compat.py`.

---

## 6. Conformidade Arquitetural (do `arquitetura.html`, se existir)

- **Regras de Acoplamento respeitadas?** Sim. O domínio (`placeholders.py`) permanece como núcleo puro sem dependências externas; a camada de tradução (`orchestrator.py`) consome o domínio; os provedores LLM interagem apenas pelas portas definidas.
- **ADRs relevantes:** Alinhado com as decisões de preservação cirúrgica de estrutura EPUB e tolerância a falhas na tradução em lote.

---

## 7. Lembrete de Atualização Arquitetural

- Esta mudança introduz componente(s), regra(s) de acoplamento ou ADR novos que ainda não estão no `docs/arquitetura/arquitetura.html`? **Não**. Trata-se de refinamento interno de funções puras e regras de fidelidade já existentes.

---

## 8. Veredito

**PODE FINALIZAR SEM RESSALVAS**
