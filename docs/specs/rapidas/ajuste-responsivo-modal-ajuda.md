# Modificação Rápida: Ajuste responsivo de proporções e scroll na tela modal de Ajuda

*(preenchido em conjunto por desenvolvedor e IA — sem debate de trade-offs, sem ADR)*

## O que muda
1. Em `HELP_CSS` (`src/tradutor/tui/screens/help.py`):
   - Atualiza `#help-dialog` para ser responsivo e adaptativo ao tamanho da janela: `width: 80; max-width: 90%; height: 85%; max-height: 40; min-height: 12;`.
   - Altera `#help-text-container` de altura rígida (`height: 16;`) para flexível (`height: 1fr; overflow-y: auto; margin-bottom: 1;`), ocupando todo o espaço vertical disponível no diálogo.
   - Define explicitamente `height: auto;` em `#help-dialog .center-row` (e em `APP_CSS` para `.center-row`), evitando que o contêiner do botão expanda indevidamente (`1fr`) e crie espaço vazio desproporcional.
2. Adiciona atalhos de fechamento (`escape`, `q`) via `BINDINGS` em `HelpScreen`, melhorando a ergonomia da navegação.
3. Adiciona testes de regressão em `tests/tui/test_app_flows.py` validando o fechamento via teclado e o comportamento em diferentes resoluções de terminal (compacto 80x24 e expandido 120x50).

## Por que
Anteriormente, o contêiner de texto `#help-text-container` possuía uma altura estática engessada em 16 linhas (`height: 16`), enquanto a linha do botão (`.center-row`) assumia o padrão `1fr` de contêineres horizontais no Textual, expandindo e ocupando todo o restante da altura do modal. Isso gerava um espaço visual excessivo e vazio ao redor do botão "Fechar" e forçava o texto a uma área minúscula de rolagem. Em variações de tamanho de janela (janelas grandes ou pequenas), a proporção ficava ainda mais distorcida ou com transbordamento. Com `height: 1fr` no texto e `height: auto` no botão, o texto aproveita dinamicamente toda a área útil da tela e o botão permanece compacto na base.

## Arquivos afetados
- `src/tradutor/tui/screens/help.py` — atualização de `HELP_CSS` e inclusão de `BINDINGS`.
- `src/tradutor/tui/app.py` — inclusão de `height: auto;` na regra global `.center-row` em `APP_CSS`.
- `tests/tui/test_app_flows.py` — testes de fechamento e responsividade do modal de ajuda.

## Risco de Regressão
Baixo — ajuste puramente visual/estilístico em CSS e inclusão de atalho de fechamento não destrutivo.

## Precisa de teste novo?
Sim: teste de TUI validando o fluxo da tela de ajuda em dimensões variadas e o fechamento por atalho de teclado (`escape`).

---

## ⚠️ Trava de Escalonamento

- Introduz um Ator/papel de usuário novo? não
- Cria ou muda uma regra de acoplamento entre componentes já registrada no `docs/arquitetura/arquitetura.html`? não
- Contraria ou exige revisar um ADR aprovado? não
- Muda comportamento observável de forma que mereça uma decisão arquitetural registrada? não
