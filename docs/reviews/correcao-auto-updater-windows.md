# Relatório de Review: Correção do Auto-Updater no Windows

*(preenchido pela IA — referência: `docs/specs/rapidas/correcao-auto-updater-windows.md`)*

---

## 1. Escopo Revisado

- **Mudança OpenSpec:** N/A (bugfix documentado via `modificacao-rapida`)
- **Spec de referência:** `docs/specs/rapidas/correcao-auto-updater-windows.md`
- **Arquivos tocados no diff (desta mudança):**
  - `src/tradutor/infra/updater.py` — substituição da rotina do updater pelo script PowerShell `update_helper.ps1`, correção de flags no `subprocess.Popen` (remoção da combinação conflitante `CREATE_NO_WINDOW | DETACHED_PROCESS`), uso de `os._exit(0)` e nova função `clear_pending_update()`.
  - `src/tradutor/tui/app.py` — `on_mount()` exibe o modal no estado `downloaded` ao detectar versão pendente, evitando timer arbitrário e loop infinito ao reabrir.
  - `src/tradutor/tui/screens/update.py` — suporte ao parâmetro `initial_state` e inclusão do botão de descarte de atualização (`#discard-btn`).
  - `tests/infra/test_updater.py` — novos testes para helper PowerShell, limpeza de cache pendente e tratamento de falha no launcher.
  - `tests/tui/test_updater_tui.py` — testes para inicialização com modal `downloaded` e ação de descarte.

---

## 2. 🔴 Bloqueadores

Nenhum bloqueador encontrado.

---

## 3. 🟡 Atenção

- **[PowerShell Execution Policy]** O script auxiliar é executado usando o parâmetro `-ExecutionPolicy Bypass`, garantindo que o PowerShell execute sem restrições mesmo em ambientes corporativos com ExecutionPolicy restritivo para o usuário atual, sem requerer privilégios de administrador.

---

## 4. 🔵 Sugestões

- Nenhum item adicional.

---

## 5. Checklist de Fitness Functions (da spec)

N/A — modificação rápida, sem checklist formal de Fitness Functions.

**"Precisa de teste novo?" (do modelo rápido):** Sim → atendido. Testes unitários e de integração TUI implementados cobrindo todos os novos comportamentos e proteções contra loops de inicialização.

---

## 6. Conformidade Arquitetural

- **Regras de Acoplamento respeitadas?** Sim. O isolamento entre `infra/updater.py` e `tui/` foi estritamente preservado. A infraestrutura não importa componentes de apresentação.
- **ADRs relevantes:** N/A.

---

## 7. Lembrete de Atualização Arquitetural

- Esta mudança introduz componente(s), regra(s) de acoplamento ou ADR novos que ainda não estão no `arquitetura.html`? Não.

---

## 8. Veredito

PODE ARQUIVAR SEM RESSALVAS
