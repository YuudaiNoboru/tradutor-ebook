# Modificação Rápida: Retomada travada após cancelamento (tela de progresso)

*(preenchido em conjunto por desenvolvedor e IA — sem debate de trade-offs, sem ADR)*

## O que muda
Cancelar uma tradução e, em seguida, selecionar o mesmo livro e clicar em
"Continuar tradução" volta para a tela de progresso reutilizando a **mesma
instância** de `ProgressScreen` (Textual 8 mantém telas instaladas montadas),
sem disparar `on_mount` novamente. Com isso `_cancel` permanece `True`, o
worker de tradução nunca é iniciado e o log mostra a mensagem antiga
"cancelamento solicitado..." — a tela fica travada sem progressão.

## Por que
Bug reportado em teste manual de persistência/reuso do guia de estilo e tom
(fluxo de retomada após cancelamento). Em Textual 8.2, `switch_screen` apenas
substitui o topo da pilha e `push_screen` reutiliza a instância registrada em
`SCREENS`; telas instaladas nunca são removidas (`_replace_screen` só remove
telas não instaladas). O único evento disparado na reentrada é `ScreenResume`,
que a `ProgressScreen` hoje não trata.

## Arquivos afetados
- `src/tradutor/tui/screens/progress.py` — tratar `ScreenResume` reiniciando o
  estado e o worker (padrão `_first_resume` já usado em `estimate.py`).
- `tests/tui/test_app_flows.py` — teste de regressão: cancelar → continuar →
  progresso retoma.

## Risco de Regressão
Médio — toca o ciclo de vida da tela de progresso (worker, handler de log do
provider e estado de cancelamento), usado em todos os fluxos de tradução.

## Precisa de teste novo?
Sim: teste de TUI que cancela uma tradução em andamento, retorna à estimativa,
clica em "Continuar traducao" e verifica que um novo worker inicia, a barra
avança e o log não fica preso em "cancelamento solicitado".

---

## ⚠️ Trava de Escalonamento

- Introduz um Ator/papel de usuário novo? não
- Cria ou muda uma regra de acoplamento entre componentes já registrada no `arquitetura.html`? não
- Contraria ou exige revisar um ADR aprovado? não
- Muda comportamento observável de forma que mereça uma decisão arquitetural registrada? não
