# Relatório de Review: Retry com backoff em escrita atômica de estado no Windows

*(preenchido pela IA — referência: `docs/specs/rapidas/retry-save-estado-windows.md`)*

---

## 1. Escopo Revisado

- **Identificador da mudança:** `retry-save-estado-windows`
- **Spec de referência:** `docs/specs/rapidas/retry-save-estado-windows.md`
- **Arquivos tocados no diff:**
  - `src/tradutor/translate/estado.py` — criação da função `safe_replace` com retentativas e backoff exponencial para absorver locks transitórios do Windows (`PermissionError` / `WinError 5` / `WinError 32`), e atualização de `save_estado`
  - `src/tradutor/translate/glossary_store.py` — uso de `safe_replace` em `save_glossary`
  - `src/tradutor/translate/__init__.py` — exportação de `safe_replace`
  - `src/tradutor/infra/secrets.py` — uso de `_safe_replace` em `EncryptedFileSecretStore._save`
  - `tests/translate/test_estado.py` — suíte de testes unitários para `safe_replace` e `save_estado` cobrindo falhas transitórias, falhas permanentes e erros não relacionados a permissões/locks

---

## 2. 🔴 Bloqueadores

Nenhum bloqueador encontrado.

---

## 3. 🟡 Atenção

Nenhum ponto de atenção encontrado.

---

## 4. 🔵 Sugestões

Nenhuma sugestão adicional.

---

## 5. Checklist de Fitness Functions (da spec)

- **N/A** — modificação rápida, sem checklist formal de Fitness Functions.
- **Teste novo verificado:** Sim, adicionados testes cobrindo:
  - `test_safe_replace_retries_on_permission_error_and_succeeds`: simulação de `PermissionError: [WinError 5]` temporário com sucesso nas repetições subsequentes.
  - `test_safe_replace_retries_on_winerror_32_and_succeeds`: simulação de `OSError: [WinError 32]` de compartilhamento transitório com sucesso.
  - `test_safe_replace_raises_permission_error_after_max_attempts`: esgotamento de tentativas com reraise e limpeza do arquivo temporário `.tmp`.
  - `test_safe_replace_raises_immediately_on_unrelated_oserror`: repasse imediato sem delays para exceções não relacionadas a lock.

---

## 6. Conformidade Arquitetural (do `arquitetura.html`, se existir)

- **Regras de Acoplamento respeitadas?** Sim, `translate` utiliza funções internas de seu próprio submódulo, e `infra` mantém sua implementação autocontida sem depender de camadas superiores.
- **ADRs relevantes:** Alinhado com D6 (Estado persistido por livro e tolerância a falhas).

---

## 7. Lembrete de Atualização Arquitetural

- Esta mudança introduz componente(s), regra(s) de acoplamento ou ADR novos que ainda não estão no `docs/arquitetura/arquitetura.html`? Não.

---

## 8. Veredito

PODE FINALIZAR SEM RESSALVAS
