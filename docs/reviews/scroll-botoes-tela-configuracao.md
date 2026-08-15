# Relatório de Review: Botões cortados ao rolar tela de configuração em tamanho reduzido

*(preenchido pela IA — referência: `docs/specs/rapidas/scroll-botoes-tela-configuracao.md` e `docs/arquitetura/arquitetura.html`)*

---

## 1. Escopo Revisado

- **Identificador da mudança:** `scroll-botoes-tela-configuracao`
- **Spec de referência:** `docs/specs/rapidas/scroll-botoes-tela-configuracao.md`
- **Arquivos tocados no diff:**
  - `src/tradutor/tui/screens/config.py`
  - `tests/tui/test_app_flows.py`

---

## 2. 🔴 Bloqueadores
*(viola regra de acoplamento do `arquitetura.html`, contraria um ADR aprovado, ou deixa um item da checklist de Fitness Functions da spec sem implementação — a mudança não deveria ser finalizada com itens aqui)*

Nenhum bloqueador encontrado.

---

## 3. 🟡 Atenção
*(caso de borda da Seção 4 da spec sem tratamento visível no código ou em teste; comportamento que diverge do fluxo descrito na Seção 4 da spec sem ser claramente uma melhoria)*

Nenhum ponto de atenção encontrado.

---

## 4. 🔵 Sugestões
*(qualidade geral fora do escopo de conformidade: nomes, duplicação, tratamento de exceção genérico, legibilidade — não bloqueiam a finalização da mudança)*

Nenhuma sugestão adicional.

---

## 5. Checklist de Fitness Functions (da spec)
*(só se aplica se a fonte for `docs/specs/<slug>.md`, formato completo — copiar os itens da Seção 6 e marcar cada um com base no diff, sem redebater se o critério em si faz sentido, só checar se foi atendido. Se a fonte for `docs/specs/rapidas/<slug>.md`, escrever "N/A — modificação rápida, sem checklist de Fitness Functions" e usar o campo "Precisa de teste novo?" do modelo-rapido no lugar.)*

- **N/A** — modificação rápida, sem checklist formal de Fitness Functions.
- **Teste novo verificado:** Sim, adicionado teste `test_config_screen_small_terminal_buttons_accessible` em `tests/tui/test_app_flows.py` validando que em viewport compacto (80x24) a tela rola até a base e o botão `#back` é acionável.

---

## 6. Conformidade Arquitetural (do `arquitetura.html`, se existir)

- **Regras de Acoplamento respeitadas?** Sim, nenhuma regra de acoplamento nova ou alterada; mudança estritamente visual/TUI.
- **ADRs relevantes:** Alinhado com D10 (TUI em Textual).

---

## 7. Lembrete de Atualização Arquitetural
*(o code-review NÃO atualiza o `arquitetura.html` — só sinaliza se é hora de rodar o `architecture-report`)*

- Esta mudança introduz componente(s), regra(s) de acoplamento ou ADR novos que ainda não estão no `docs/arquitetura/arquitetura.html`? Não.

---

## 8. Veredito

PODE FINALIZAR SEM RESSALVAS
