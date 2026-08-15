# Modificação Rápida: Persistência do tema visual selecionado no config.toml

*(preenchido em conjunto por desenvolvedor e IA — sem debate de trade-offs, sem ADR)*

## O que muda
1. Em `AppConfig` (`src/tradutor/infra/config.py`):
   - Adiciona o campo `theme: str = "textual-dark"` ao modelo de configuração.
   - Atualiza `write_config` para serializar o campo `theme` no `config.toml`.
2. Em `TradutorApp` (`src/tradutor/tui/app.py`):
   - No método `on_mount()`, restaura o tema configurado (`self.theme = self.env.config.theme`).
   - Implementa o observador reativo `watch_theme(self, theme: str) -> None` para salvar automaticamente qualquer alteração de tema feita pelo usuário no `config.toml`.
3. Adiciona testes em `tests/infra/test_config.py` e `tests/tui/test_app_flows.py` validando o carregamento, salvamento e persistência do tema.

## Por que
Quando o usuário escolhe um tema na interface (via Command Palette no cabeçalho), a preferência ficava apenas na memória da sessão e era perdida ao fechar o aplicativo. Salvar o tema no `config.toml` e recarregá-lo na inicialização garante que a experiência visual personalizada seja preservada entre execuções.

## Arquivos afetados
- `src/tradutor/infra/config.py` — campo `theme` e serialização TOML.
- `src/tradutor/tui/app.py` — aplicação do tema no `on_mount` e observador `watch_theme`.
- `tests/infra/test_config.py` — teste de carga/escrita do campo `theme`.
- `tests/tui/test_app_flows.py` — teste de persistência reativa de tema.

## Risco de Regressão
Baixo — campo com default retrocompatível (`textual-dark`) e salvamento não bloqueante.

## Precisa de teste novo?
Sim: teste de infraestrutura validando TOML com `theme` e teste de TUI validando `watch_theme`.

---

## ⚠️ Trava de Escalonamento

- Introduz um Ator/papel de usuário novo? não
- Cria ou muda uma regra de acoplamento entre componentes já registrada no `docs/arquitetura/arquitetura.html`? não
- Contraria ou exige revisar um ADR aprovado? não
- Muda comportamento observável de forma que mereça uma decisão arquitetural registrada? não
