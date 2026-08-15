# Modificação Rápida: Redesenho do painel de progresso da tela de tradução (dashboard com cards e registro de atividades)

*(preenchido em conjunto por desenvolvedor e IA — sem debate de trade-offs, sem ADR)*

## O que muda
1. Em `ProgressScreen` (`src/tradutor/tui/screens/progress.py`):
   - Configura o `ProgressBar` com `show_eta=False` e `show_percentage=True` para evitar a colisão de textos (`53%00:00:31`).
   - Substitui as linhas soltas de texto por um painel de cartões de métricas (dashboard com 3 colunas):
     - **BLOCOS**: Progresso numérico claro (`X / Y blocos`).
     - **DECORRIDO**: Tempo decorrido desde o início da tradução (em português, ex.: `0 s`, `31 s`, `1.5 min`).
     - **RESTANTE**: Tempo restante estimado sem siglas em inglês (`~31 s`, `calculando...`).
   - Adiciona rótulo explicativo antes da área de mensagens: `"Registro de Atividades"`.
   - Ajusta alturas e espaçamentos no `PROGRESS_CSS` para garantir harmonia visual e responsividade vertical.
2. Em testes (`tests/tui/test_app_flows.py`):
   - Adiciona / atualiza testes de TUI verificando os componentes de métricas da `ProgressScreen`.

## Por que
A apresentação anterior exibia números grudados (`53%00:00:31`) devido à formatação padrão do componente do Textual, utilizava a sigla técnica em inglês `ETA` (pouco amigável para o usuário) e espalhava os dados de progresso e tempo em linhas soltas sem hierarquia visual clara. A nova organização em cards de métricas e seção rotulada de log torna a tela intuitiva, moderna e visualmente equilibrada.

## Arquivos afetados
- `src/tradutor/tui/screens/progress.py`
- `tests/tui/test_app_flows.py`

## Risco de Regressão
Baixo — refinamento puramente visual e de usabilidade na interface TUI, sem alteração no pipeline ou no barramento de eventos de tradução.

## Precisa de teste novo?
Sim: teste de TUI validando a renderização dos cartões de métricas e atualização de valores durante eventos de progresso.

---

## ⚠️ Trava de Escalonamento

- Introduz um Ator/papel de usuário novo? não
- Cria ou muda uma regra de acoplamento entre componentes já registrada no `docs/arquitetura/arquitetura.html`? não
- Contraria ou exige revisar um ADR aprovado? não
- Muda comportamento observável de forma que mereça uma decisão arquitetural registrada? não
