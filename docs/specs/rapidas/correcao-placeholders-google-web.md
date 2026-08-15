# Modificação Rápida: Preservação de Placeholders e Tolerância Estrutural no Google Web

*(preenchido em conjunto por desenvolvedor e IA — sem debate de trade-offs, sem ADR)*

## O que muda

1. **Proteção de Placeholders no Endpoint HTML (`/translateHtml`)**:
   - Em `src/tradutor/providers/machine_translation/google_web.py`, envelopar todos os placeholders `{{N}}` em nós `<span class="notranslate">{{N}}</span>` (ou `translate="no"`) antes de enviar o payload ao endpoint HTML.
   - O Google Translate respeita nativamente tags com classe `notranslate` e atributo `translate="no"`, preservando o nó DOM intacto na tradução sem descartar nem corromper seu conteúdo interno.
   - Ao receber a resposta, remover a tag envolvente `<span>`, restaurando os placeholders `{{N}}` originais de forma determinística.

2. **Normalização e Descolamento de Placeholders em Palavras (`extract_protected`)**:
   - Em `src/tradutor/domain/placeholders.py`, garantir que placeholders embutidos sem espaço adjacente a caracteres alfanuméricos (`word{{0}}` ou `{{0}}word`) sejam separados com espaço durante a extração de conteúdo protegido, estendendo a lógica de `normalize_hyphenated_placeholders`.
   - Isso impede que o motor neural de tradução veja o placeholder como parte integrante de um vocábulo ou expressão idiomática (ex.: `flying by the {{0}}seat of their pants` -> `flying by the {{0}} seat of their pants`).

3. **Proteção no Fallback Textual e Limpeza**:
   - No fallback textual do `GoogleWebProvider`, garantir que placeholders `{{N}}` também sejam mascarados com tokens `@@N@@` antes do envio a `/translate_a/t` e desmascarados por `unmask_markup`.
   - Ajustar `clean_placeholders` para tolerar variações de chaves com espaçamentos múltiplos (ex.: `{ { 0 } }` ou `@ @ 0 @ @`).
   - Evitar que uma falha de fidelidade de formatação pontual em um bloco desative permanentemente o endpoint HTML para todo o resto do livro.

4. **Refinamento de Detecção de Marcas de IA (`has_ai_mark`)**:
   - Em `src/tradutor/domain/quality.py`, refinar `_AI_MARK_PATTERNS` para restringir a detecção de notas em colchetes a marcadores explícitos de tradução/IA (como `[Nota de tradução: ...]`, `[Tradução automática]`, `[Tradução: ...]`, `[N.T.]`, `[Original: ...]`, `[Texto original: ...]`).
   - Evitar falso-positivo em parágrafos de prosa legítima do autor delimitados por colchetes que contenham vocábulos comuns como "original" ou "tradução" (ex.: bloco 3617 de `app02.html`: `[Discussion of implementation challenges. In Alexander's original format...]`).

5. **Testes Unitários e de Regressão**:
   - Testes unitários para `GoogleWebProvider` verificando tradução HTML com placeholders em expressões idiomáticas e sem perda de tokens.
   - Testes de extração em `test_placeholders.py` verificando descolamento de placeholders colados em palavras.
   - Testes em `test_quality.py` validando que notas legítimas de autor entre colchetes não são reprovadas como marcas de IA.

## Por que

- Durante a tradução de `ddd.epub` usando o provedor Google Web (experimental):
  1. A tradução quebrou inicialmente com `GoogleWebResponseError: resposta alterou placeholder do bloco 280` devido ao descarte do token `{{0}}` colado à expressão idiomática em `pref03.html`.
  2. Após a correção dos placeholders, a tradução falhou no final com `TranslationQualityError: resposta reprovada na verificacao de qualidade para 1 bloco(s)` no bloco 3617 (`app02.html`). O bloco continha um parágrafo do autor entre colchetes citando "formato original de Alexander", disparando indevidamente a regex genérica de detecção de marcas de IA (`has_ai_mark`).

## Arquivos afetados

- `src/tradutor/domain/placeholders.py` — limpeza tolerante de chaves em placeholders.
- `src/tradutor/domain/quality.py` — refinamento dos padrões de notas de IA/tradução entre colchetes em `has_ai_mark`.
- `src/tradutor/providers/machine_translation/google_web.py` — envelopamento de placeholders com `<span class="notranslate">` e isolamento de fallback por lote.
- `tests/domain/test_placeholders.py` — testes unitários para limpeza de chaves aninhadas.
- `tests/domain/test_quality.py` — testes unitários para notas de autor vs notas de IA entre colchetes.
- `tests/providers/test_google_web.py` — testes de tradução com placeholders em HTML.

## Risco de Regressão

**Baixo** — Refinamento de expressões regulares de controle de qualidade e transporte sem alteração de contratos públicos.

## Precisa de teste novo?

**Sim**:
- Teste de `clean_placeholders` com chaves espaçadas.
- Testes no `test_google_web.py` validando envelopamento/desenvelopamento de `<span class="notranslate">`.
- Testes no `test_quality.py` garantindo que prosa legítima de autor em colchetes não seja rejeitada.

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
  1. `_protect_html_placeholders` e `_unprotect_html_placeholders` adicionados em `src/tradutor/providers/machine_translation/google_web.py` para envelopar `{{N}}` em `<span class="notranslate">{{N}}</span>` (ou `translate="no"`) e restaurá-los de volta após o parsing de resposta HTML.
  2. `_translate_group` aprimorado para isolar falhas de formatação HTML pontuais sem desativar o endpoint HTML globalmente para lotes futuros do livro.
  3. `clean_placeholders` em `src/tradutor/domain/placeholders.py` atualizado com suporte a variações de espaços múltiplos aninhados em chaves e marcadores.
  4. `_AI_MARK_PATTERNS` em `src/tradutor/domain/quality.py` refinado para evitar falso-positivo em parágrafos de autor entre colchetes.
  5. Testes unitários adicionados em `tests/domain/test_placeholders.py`, `tests/domain/test_quality.py` e `tests/providers/test_google_web.py`.
- **Validação Final:** 666 testes aprovados no `pytest`, 0 erros no lint (`hatch run lint`), formatação checada (`hatch run fmt-check`) e cobertura de 95% (`hatch run cov`).
