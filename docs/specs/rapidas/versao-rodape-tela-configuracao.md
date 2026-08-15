# Modificação Rápida: Exibição consistente da versão do app no rodapé de todas as telas (incluindo Configuração)

*(preenchido em conjunto por desenvolvedor e IA — sem debate de trade-offs, sem ADR)*

## O que muda
1. Em `src/tradutor/tui/screens/config.py` (`FORM_CSS`):
   - Escopa a regra de estilo `Label { margin-top: 1; }` para `#config-form Label { margin-top: 1; }`.
2. Em `src/tradutor/tui/widgets.py` (`VersionFooter`):
   - `VersionFooter` é um contêiner composto (`Widget`) com `layout: horizontal; dock: bottom; height: 1; width: 100%; background: $footer-background;`.
   - `Footer` interno recebe `dock: none; width: 1fr; height: 1; background: $footer-background;`.
   - `Label` com a versão (`.-version-label`) recebe `dock: none; width: auto; height: 1; margin: 0; padding: 0 1; background: $footer-background; color: $text-muted; text-opacity: 85%;`.
3. Em `src/tradutor/tui/app.py`:
   - `TradutorApp` mantém `ENABLE_COMMAND_PALETTE = False`.
4. Adiciona teste em `tests/tui/test_app_flows.py` validando que `VersionFooter` renderiza a versão (`.-version-label`) tanto na tela principal quanto na tela de configuração.

## Por que
Na tela de Configuração (`ConfigScreen`), existia uma regra genérica de CSS `Label { margin-top: 1; }`. Como o `VersionFooter` é um contêiner de apenas 1 linha de altura (`height: 1`), essa regra empurrava o widget `Label` da versão em 1 linha para baixo (`margin-top: 1`), fazendo com que ele ficasse deslocado para fora da área visível do rodapé exclusivamente nessa tela. Ao escopar a regra para `#config-form Label` e fixar `margin: 0; dock: none;` no `.-version-label`, a versão permanece visível e perfeitamente alinhada em todas as telas do aplicativo.

## Arquivos afetados
- `src/tradutor/tui/screens/config.py` — escopo de `Label` no `FORM_CSS`.
- `src/tradutor/tui/widgets.py` — `DEFAULT_CSS` refinado com `dock: none; margin: 0;` para os componentes filhos do `VersionFooter`.
- `src/tradutor/tui/app.py` — desativação da Command Palette nativa.
- `tests/tui/test_app_flows.py` — teste de conformidade do rodapé.

## Risco de Regressão
Baixo — correção de seletor CSS e estabilização de estilos de rodapé.

## Precisa de teste novo?
Sim: teste de TUI validando a renderização do `.-version-label` na `BookScreen` e `ConfigScreen`.

---

## ⚠️ Trava de Escalonamento

- Introduz um Ator/papel de usuário novo? não
- Cria ou muda uma regra de acoplamento entre componentes já registrada no `docs/arquitetura/arquitetura.html`? não
- Contraria ou exige revisar um ADR aprovado? não
- Muda comportamento observável de forma que mereça uma decisão arquitetural registrada? não
