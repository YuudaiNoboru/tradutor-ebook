## Why

Atualmente, o módulo de interface gráfica (TUI) do `tradutor-ebook` encontra-se fortemente acoplado ao motor de tradução e à infraestrutura técnica. As telas de terminal importam e gerenciam de forma síncrona fluxos de rede, leitura/escrita física de arquivos EPUB e estimativa de custos. 

Esta mudança visa desacoplar a camada de visualização (TUI) do motor de tradução, delegando a lógica técnica de negócios a um pipeline e a um planejador agnósticos. A comunicação entre o motor (que roda em threads secundárias) e a TUI será feita de forma reativa através de um padrão de observador (Observer Pattern / Callbacks baseados em Eventos Thread-Safe), eliminando o acoplamento direto de concorrência e assinaturas de callbacks síncronos e facilitando a testabilidade (Testability) e a evolutividade (Evolvability) estrutural do projeto.

## What Changes

- **Extração da lógica do TUI Runner**: Toda a orquestração do fluxo de tradução de e-books que reside em [runner.py](file:///C:/Users/vasco/Software/tradutor-ebook/src/tradutor/tui/runner.py) será migrada para a camada core em `src/tradutor/translate/` em um novo módulo de pipeline (`translate/pipeline.py` ou integrado a `translate/orchestrator.py`).
- **Extração da lógica de custos e estimativas**: A estimativa de tokens, volumetria e custos sairá do TUI runner e irá para um novo módulo de planejamento (`translate/planner.py`).
- **Implementação do Observer Pattern**: A comunicação baseada em callbacks individuais do `RunnerHooks` será substituída por notificações baseadas em eventos thread-safe de domínio agnóstico (dataclasses de eventos), permitindo que a TUI reaja enviando mensagens thread-safe no loop de renderização do Textual (`post_message`).
- **Centralização do teste de conexão dos provedores**: A lógica de rede de teste de chaves de API e conexões em `screens/config.py` será centralizada em um serviço de provedores sob a pasta `providers/`.

## Capabilities

### New Capabilities
*(Não há novas capacidades funcionais observáveis de comportamento, pois se trata de uma refatoração arquitetural interna pura. `skip_specs: true` foi ativado nas configurações do OpenSpec).*

### Modified Capabilities
*(Nenhuma).*

## Impact

- **Código Afetado**: 
  - Subpacote `src/tradutor/tui/` (principalmente [runner.py](file:///C:/Users/vasco/Software/tradutor-ebook/src/tradutor/tui/runner.py) que será eliminado, além de [app.py](file:///C:/Users/vasco/Software/tradutor-ebook/src/tradutor/tui/app.py) e telas em `tui/screens/` como [progress.py](file:///C:/Users/vasco/Software/tradutor-ebook/src/tradutor/tui/screens/progress.py), [estimate.py](file:///C:/Users/vasco/Software/tradutor-ebook/src/tradutor/tui/screens/estimate.py) e [config.py](file:///C:/Users/vasco/Software/tradutor-ebook/src/tradutor/tui/screens/config.py)).
  - Subpacote `src/tradutor/translate/` onde serão criados os novos componentes de pipeline e barramento de eventos.
  - Subpacote `src/tradutor/providers/` que absorverá a lógica de testes de conexões de rede de provedores.
- **APIs & Dependências**: Sem alterações nas dependências externas.
- **Suíte de Testes**: Permite expandir testes de integração em `tests/` para testar o pipeline completo de tradução sem instanciar frames da TUI.
