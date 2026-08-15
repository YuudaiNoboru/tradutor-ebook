# Modificação Rápida: Botões cortados ao rolar tela de configuração em tamanho reduzido

*(preenchido em conjunto por desenvolvedor e IA — sem debate de trade-offs, sem ADR)*

## O que muda
Alinha o comportamento da `ConfigScreen` com a tela de seleção de arquivos (`BookScreen`), onde o scroll é gerenciado diretamente pela `Screen` nativa:
1. Em `FORM_CSS`, remove `max-height: 100%;` e `overflow-y: auto;` de `#config-form`, definindo `height: auto; margin-bottom: 1;`.
2. Mantém `#config-form` como `Vertical(id="config-form")`.
3. Com isso, em janelas de tamanho reduzido, o Textual gerencia o overflow e a rolagem da `Screen` por completo, permitindo que a rolagem chegue até a base da tela e exiba os botões de ação (`Testar conexao`, `Salvar`, `Voltar`) com margem inferior limpa acima do rodapé.

## Por que
A `BookScreen` funciona perfeitamente em telas pequenas porque deixa a rolagem a cargo da `Screen` sem criar contêineres roláveis internos artificiais com limites rígidos. Na `ConfigScreen`, a presença de `max-height: 100%` e `overflow-y: auto` em `#config-form` criava um contêiner restrito com altura engessada que conflitava com a área útil do terminal, impedindo que os botões inferiores fossem totalmente revelados ao rolar.

## Arquivos afetados
- `src/tradutor/tui/screens/config.py` — alteração em `FORM_CSS` para definir `height: auto; margin-bottom: 1;` sem `overflow-y: auto` ou `max-height: 100%`.
- `tests/tui/test_app_flows.py` — teste de regressão `test_config_screen_small_terminal_buttons_accessible` em tamanho compacto (80x24).

## Risco de Regressão
Baixo — padronização do padrão de layout com as demais telas do aplicativo (`BookScreen`, `EstimateScreen`).

## Precisa de teste novo?
Sim: teste de TUI em tamanho compacto (80x24) validando que a tela rola até o final e permite a ativação do botão `#back`.

---

## ⚠️ Trava de Escalonamento

- Introduz um Ator/papel de usuário novo? não
- Cria ou muda uma regra de acoplamento entre componentes já registrada no `docs/arquitetura/arquitetura.html`? não
- Contraria ou exige revisar um ADR aprovado? não
- Muda comportamento observável de forma que mereça uma decisão arquitetural registrada? não
