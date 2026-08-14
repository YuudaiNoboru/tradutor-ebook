# Modificação Rápida: Padronização visual de alinhamento, espaçamento e proporções em todas as telas da TUI

*(preenchido em conjunto por desenvolvedor e IA — sem debate de trade-offs, sem ADR)*

## O que muda
1. Em `APP_CSS` (`src/tradutor/tui/app.py`):
   - Define o alinhamento padrão de telas comuns como `Screen { align: center top; }`, posicionando o conteúdo de forma limpa e natural abaixo do cabeçalho.
   - Mantém `ModalScreen { align: center middle; }` para garantir que telas modais/diálogos fiquem perfeitamente centralizadas.
   - Padroniza tipografia e espaçamentos globais de títulos, hints e diálogos de erro.
2. Em todas as telas principais:
   - `WelcomeScreen` (`src/tradutor/tui/screens/welcome.py`): define largura consistente (`width: 80; max-width: 90%; margin-top: 2;`).
   - `BookScreen` (`src/tradutor/tui/screens/book.py`): consolidado com `BookScreen { align: center top; }`, `#book-form` com `width: 80; height: auto; margin-top: 1;` e árvore com `height: 15;`.
   - `ConfigScreen` (`src/tradutor/tui/screens/config.py`): formulário com `width: 82; max-width: 95%; margin-top: 1;` e espaçamentos harmônicos.
   - `EstimateScreen` (`src/tradutor/tui/screens/estimate.py`): `#estimate-view` com `width: 84; max-width: 95%; margin-top: 1;`.
   - `ProgressScreen` (`src/tradutor/tui/screens/progress.py`): `#progress-view` com `width: 84; max-width: 95%; margin-top: 1;`, botão de cancelamento encapsulado em `.center-row` e log com altura proporcional.
   - `ReportScreen` (`src/tradutor/tui/screens/report.py`): `#report-view` com `width: 84; max-width: 95%; margin-top: 1;`.
3. Em telas modais:
   - `ErrorScreen` (`src/tradutor/tui/screens/error.py`): diálogo de erro com `max-width: 90%` e espaçamento padronizado.
   - `HelpScreen` (`src/tradutor/tui/screens/help.py`): proporção 85% e rolagem fluida.
   - `UpdateModal` (`src/tradutor/tui/screens/update.py`): diálogo com `max-width: 90%`.
4. Atualiza e expande os testes em `tests/tui/test_app_flows.py` para garantir a conformidade dos componentes.

## Por que
Antes, havia discrepâncias visuais entre as telas: algumas herdavam `align: center middle` flutuando no meio do terminal com vácuo superior excessivo, outras possuíam larguras divergentes (80, 82, 84, 90) ou botões desalinhados (como o botão de cancelamento no progresso sem `.center-row`). A padronização cria uma identidade visual uniforme, limpa e profissional para todo o aplicativo.

## Arquivos afetados
- `src/tradutor/tui/app.py`
- `src/tradutor/tui/screens/welcome.py`
- `src/tradutor/tui/screens/book.py`
- `src/tradutor/tui/screens/config.py`
- `src/tradutor/tui/screens/estimate.py`
- `src/tradutor/tui/screens/progress.py`
- `src/tradutor/tui/screens/report.py`
- `tests/tui/test_app_flows.py`

## Risco de Regressão
Baixo — refinamentos estritamente visuais de CSS sem alteração de contratos ou regras de negócio.

## Precisa de teste novo?
Sim: teste de TUI validando a consistência dos contêineres e fluxo entre as telas.

---

## ⚠️ Trava de Escalonamento

- Introduz um Ator/papel de usuário novo? não
- Cria ou muda uma regra de acoplamento entre componentes já registrada no `docs/arquitetura/arquitetura.html`? não
- Contraria ou exige revisar um ADR aprovado? não
- Muda comportamento observável de forma que mereça uma decisão arquitetural registrada? não
