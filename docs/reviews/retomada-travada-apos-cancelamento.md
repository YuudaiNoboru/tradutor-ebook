# Relatório de Review: Retomada travada após cancelamento (tela de progresso)

*(preenchido pela IA — referência: `docs/specs/rapidas/retomada-travada-apos-cancelamento.md`)*

---

## 1. Escopo Revisado

- **Mudança OpenSpec:** N/A (bugfix documentado via `modificacao-rapida`, fora do ciclo Apply/Archive de uma change)
- **Spec de referência:** `docs/specs/rapidas/retomada-travada-apos-cancelamento.md` (formato reduzido)
- **Arquivos tocados no diff (desta mudança):**
  - `src/tradutor/tui/screens/progress.py` — extrai `start_run()` (estado + worker) de `on_mount`; reset de UI (botão, log, barra, contador, ETA) na reentrada
  - `src/tradutor/tui/screens/estimate.py` — `_start` chama `progress.start_run()` quando a tela já está montada
  - `tests/epub/builders.py` — novo builder `build_epub3_many_chapters(count)`
  - `tests/tui/test_app_flows.py` — novo teste `test_resume_after_cancel_restarts_progress_worker`

---

## 2. 🔴 Bloqueadores

Nenhum bloqueador encontrado.

---

## 3. 🟡 Atenção

- **[tests/epub/builders.py / estimate.py]** O diff ficou um pouco maior que o declarado em "Arquivos afetados" da spec rápida: além de `progress.py` e `test_app_flows.py`, tocou `estimate.py` (necessário — a retomada precisa partir de um iniciador explícito, e o evento `ScreenResume` se mostrou ambíguo: `pop_screen` também o dispara ao dispensar o modal de erro) e `tests/epub/builders.py` (fixture multi-capítulo para deixar blocos pendentes na 1ª execução, sem a qual o teste não observa a retomada). Ampliação justificada, sem impacto no desenho.

---

## 4. 🔵 Sugestões

- **[src/tradutor/tui/screens/estimate.py:283]** O acoplamento `estimate → progress.start_run()` é direto entre telas (chamada a método público da outra tela via `app.get_screen`). Alternativa seria um evento de domínio/mensagem própria; aceitável no estado atual da TUI, onde `set_notice`/`switch_screen` já seguem o mesmo padrão.

---

## 5. Checklist de Fitness Functions (da spec)

N/A — modificação rápida, sem checklist de Fitness Functions.

**"Precisa de teste novo?" (do modelo rápido):** Sim → atendido. `test_resume_after_cancel_restarts_progress_worker` cobre: cancelamento no 1º lote → retorno à estimativa com "Continuar traducao" → nova execução com worker reiniciado (botão cancelar reabilitado, log limpo, sem a mensagem presa "cancelamento solicitado") → leitura do `priming.txt` de disco sem nova chamada de passada (`len(provider.calls)` estável) → conclusão com mais chamadas de tradução. Suíte: 577 testes verdes; lint e fmt-check limpos; cobertura total 95% (gate >= 95% atendido).

---

## 6. Conformidade Arquitetural (do `arquitetura.html`, se existir)

- **Regras de Acoplamento respeitadas?** Não verificável — `docs/arquitetura/arquitetura.html` não existe neste repositório (pastas presentes: `fundacao`, `novas-funcoes`, `reviews`, `specs`). Review prosseguiu sem essa camada.
- **ADRs relevantes:** N/A (sem painel arquitetural para consultar). A mudança não cria componente novo nem regra de acoplamento — opera dentro das telas existentes e segue o padrão já usado em `estimate.py` (`_first_resume`/`recompute`).

---

## 7. Lembrete de Atualização Arquitetural

- Esta mudança introduz componente(s), regra(s) de acoplamento ou ADR novos que ainda não estão no `arquitetura.html`? Não — sem componentes novos; apenas correção de ciclo de vida da `ProgressScreen`.

---

## 8. Veredito

PODE ARQUIVAR SEM RESSALVAS
