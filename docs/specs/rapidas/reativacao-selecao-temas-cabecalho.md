# Modificação Rápida: Reativação da seleção de temas via menu no cabeçalho sem poluir o rodapé

*(preenchido em conjunto por desenvolvedor e IA — sem debate de trade-offs, sem ADR)*

## O que muda
1. Em `TradutorApp` (`src/tradutor/tui/app.py`):
   - Reativa a Command Palette do Textual (`ENABLE_COMMAND_PALETTE = True`), permitindo que o ícone de menu no cabeçalho (`Header`) abra a paleta de comandos para seleção de temas (ex: `textual-dark`, `textual-light`, `dracula`, `nord`, `tokyo-night`) e alternância de modo escuro/claro.
2. Em `VersionFooter` (`src/tradutor/tui/widgets.py`):
   - Configura `Footer(show_command_palette=False)`, instruindo o rodapé a ocultar o atalho `^p palette` da barra inferior.
3. Adiciona teste em `tests/tui/test_app_flows.py` validando que a Command Palette está habilitada e que o rodapé permanece com a versão limpa.

## Por que
O usuário deseja ter acesso à troca de temas pelo menu do cabeçalho da interface sem que o atalho `^p palette` volte a ocupar espaço no rodapé ao lado das teclas de atalho da aplicação. O Textual suporta nativamente a propriedade `show_command_palette=False` no widget `Footer`, permitindo manter a Command Palette ativa na aplicação (e no cabeçalho) enquanto preserva o rodapé limpo com atalhos à esquerda e a versão à direita.

## Arquivos afetados
- `src/tradutor/tui/app.py` — remoção de `ENABLE_COMMAND_PALETTE = False` (ou reativação com `True`).
- `src/tradutor/tui/widgets.py` — passagem de `show_command_palette=False` para o `Footer`.
- `tests/tui/test_app_flows.py` — testes de conformidade.

## Risco de Regressão
Baixo — reativação de recurso nativo com supressão do indicador no rodapé.

## Precisa de teste novo?
Sim: teste de TUI validando que o `VersionFooter` e a versão permanecem corretos com a Command Palette ativa.

---

## ⚠️ Trava de Escalonamento

- Introduz um Ator/papel de usuário novo? não
- Cria ou muda uma regra de acoplamento entre componentes já registrada no `docs/arquitetura/arquitetura.html`? não
- Contraria ou exige revisar um ADR aprovado? não
- Muda comportamento observável de forma que mereça uma decisão arquitetural registrada? não
