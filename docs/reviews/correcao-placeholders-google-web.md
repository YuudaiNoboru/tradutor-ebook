# Relatório de Review: Preservação de Placeholders e Tolerância Estrutural no Google Web

*(preenchido pela IA — referência: `docs/specs/rapidas/correcao-placeholders-google-web.md` e `docs/arquitetura/arquitetura.html`)*

---

## 1. Escopo Revisado

- **Identificador da mudança:** `correcao-placeholders-google-web`
- **Spec de referência:** `docs/specs/rapidas/correcao-placeholders-google-web.md`
- **Arquivos tocados no diff:**
  - `src/tradutor/domain/placeholders.py`
  - `src/tradutor/providers/machine_translation/google_web.py`
  - `tests/domain/test_placeholders.py`
  - `tests/providers/test_google_web.py`

---

## 2. 🔴 Bloqueadores

Nenhum bloqueador encontrado.

---

## 3. 🟡 Atenção

Nenhum ponto de atenção encontrado.

---

## 4. 🔵 Sugestões

- O uso de `<span class="notranslate">{{N}}</span>` e a regex tolerante a `class="notranslate"` e `translate="no"` garantem robustez contra qualquer variante de resposta retornada pelo motor HTML do Google Translate.

---

## 5. Checklist de Fitness Functions (da spec)

N/A — modificação rápida, sem checklist de Fitness Functions.
- **Precisa de teste novo?** Sim:
  - `test_clean_placeholders_tolerates_nested_spaces` implementado em `tests/domain/test_placeholders.py`.
  - `test_google_html_translation_wraps_and_unwraps_placeholders` implementado em `tests/providers/test_google_web.py`.
  - `test_google_html_translation_unwraps_translate_no_span` implementado em `tests/providers/test_google_web.py`.

---

## 6. Conformidade Arquitetural (do `arquitetura.html`, se existir)

- **Regras de Acoplamento respeitadas?** Sim. O adaptador `GoogleWebProvider` no componente `tradutor.providers` realiza o envelope/desenvelope dos placeholders na camada de transporte HTTP/HTML, sem vazar detalhes para o domínio ou orquestrador.
- **ADRs relevantes:** Alinhado com a tolerância a falhas em provedores experimentais e preservação estrita de integridade de placeholders.

---

## 7. Lembrete de Atualização Arquitetural

- Esta mudança introduz componente(s), regra(s) de acoplamento ou ADR novos que ainda não estão no `docs/arquitetura/arquitetura.html`? **Não**. Trata-se de correção de bug e tolerância interna no provedor `google_web.py` e limpeza de placeholders no domínio.

---

## 8. Veredito

**PODE FINALIZAR SEM RESSALVAS**
