## 1. Estruturação dos Eventos e Domínio

- [x] 1.1 Criar o arquivo `src/tradutor/domain/events.py` definindo a classe base `TranslationEvent` e as subclasses `TranslationStartedEvent`, `TranslationProgressEvent`, `TranslationLogEvent` e `TranslationCompletedEvent`.

## 2. Extração do Planejador e Estado

- [x] 2.1 Criar o módulo `src/tradutor/translate/planner.py`.
- [x] 2.2 Migrar as funções `plan_book` e `cache_status` de `src/tradutor/tui/runner.py` para o novo módulo `planner.py`, removendo dependências de imports do subpacote `tui`.
- [x] 2.3 Ajustar as propriedades e métodos auxiliares do `AppConfig` em `src/tradutor/infra/config.py` para absorver as utilidades de extração de modelo (`model_for`) e políticas (`term_policy`).

## 3. Implementação do Pipeline e Remoção do Runner Obsoleto

- [x] 3.1 Criar o módulo `src/tradutor/translate/pipeline.py`.
- [x] 3.2 Implementar a lógica de coordenação completa da tradução em `pipeline.py` adaptando o motor para invocar `on_event(event)` a cada mudança de estado da tradução em vez dos callbacks síncronos individuais do `RunnerHooks`.
- [x] 3.3 Apagar o arquivo obsoleto `src/tradutor/tui/runner.py`.

## 4. Refatoração da Camada de Provedores

- [x] 4.1 Consolidar a lógica de teste de conexão com o endpoint em `src/tradutor/providers/` (no módulo base de tradutores ou `discovery.py`).

## 5. Acoplamento e Reação de Eventos nas Telas da TUI

- [ ] 5.1 Atualizar `src/tradutor/tui/screens/config.py` para consumir a lógica centralizada de teste de conexão e remover dependências de infraestrutura direta na UI.
- [ ] 5.2 Atualizar `src/tradutor/tui/screens/estimate.py` para consumir o novo módulo de planejamento (`translate/planner.py`).
- [ ] 5.3 Atualizar `src/tradutor/tui/screens/progress.py` para criar o pipeline passando o callback `on_event(event)` thread-safe que redireciona as notificações usando `self.post_message(event)`.

## 6. Testes Automatizados e Validação

- [ ] 6.1 Adicionar testes unitários completos em `tests/` cobrindo o ciclo de execução do `translate/pipeline.py` de forma independente da interface de terminal.
- [ ] 6.2 Validar formatação, lint e cobertura (`hatch run lint` e `hatch run cov` acima do gate de 95%).
