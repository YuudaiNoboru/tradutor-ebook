## Context

Veja `proposal.md - Why`. Atualmente, a camada de TUI controla a execução e a infraestrutura técnica por meio de [runner.py](file:///C:/Users/vasco/Software/tradutor-ebook/src/tradutor/tui/runner.py), gerando forte acoplamento e dificultando testes de integração sem frames de tela ativos.

## Goals / Non-Goals

**Goals:**
- Mudar a orquestração do pipeline completo de tradução para um novo módulo `src/tradutor/translate/pipeline.py` na camada core.
- Isolar a lógica de cálculo de volumetria e estimativa de custos para um novo módulo `src/tradutor/translate/planner.py` (ou em `domain/cost.py`).
- Implementar o padrão Observer usando dataclasses de eventos puros do Python para comunicação unidirecional (Core $\rightarrow$ UI).
- Garantir que a TUI reaja a eventos disparados pelo worker de forma thread-safe usando `self.post_message(event)` do Textual.
- Centralizar o teste de conexão de provedores sob a camada de provedores (`providers/`).
- Habilitar testes de integração automatizados do pipeline em `tests/` que não necessitem instanciar widgets de tela.

**Non-Goals:**
- Reescrever o motor de tradução para rodar sob o paradigma assíncrono do `asyncio` (`async`/`await`). A execução de chamadas bloqueantes de rede continuará rodando em threads secundárias (`ThreadPoolExecutor`).
- Mudar o comportamento visual ou a ordem das telas da TUI.

## Decisions

### 1. Comunicação por Barramento de Eventos (Observer Pattern) com Dataclasses de Eventos
Optamos pelo **Observer Pattern** (Opção B) no qual o motor de tradução aceita um callback unificado de recebimento de eventos do tipo `on_event: Callable[[TranslationEvent], None]`. 

* **Eventos de Domínio**: Definiremos as seguintes dataclasses puras em `src/tradutor/domain/events.py` (ou em `translate/pipeline.py`):
  ```python
  from dataclasses import dataclass
  from tradutor.domain import Usage


  class TranslationEvent:
      """Classe base de evento de tradução."""

      pass


  @dataclass(frozen=True)
  class TranslationStartedEvent(TranslationEvent):
      total_blocks: int


  @dataclass(frozen=True)
  class TranslationProgressEvent(TranslationEvent):
      done: int
      total: int


  @dataclass(frozen=True)
  class TranslationLogEvent(TranslationEvent):
      message: str


  @dataclass(frozen=True)
  class TranslationCompletedEvent(TranslationEvent):
      translations: dict[str, dict[int, str]]
      usage: Usage
  ```

* **Comunicação Segura de Threads (UI)**: O callback injetado pela TUI repassa o evento diretamente para o Textual:
  ```python
  def on_event(event: TranslationEvent) -> None:
      self.post_message(event)  # post_message do Textual é nativamente thread-safe
  ```

* **Alternativas Consideradas**:
  - **Fila física `queue.Queue` (Opção A)**: Exigiria que a TUI rodasse uma tarefa ativa (polling) em loop contínuo para verificar a chegada de novas mensagens, gerando complexidade adicional na TUI.
  - **Reescrita com `asyncio.Queue` (Opção C)**: Exigiria reescrever o motor síncrono para assíncrono. Descartado pelo risco e overhead de refatoração do core estável.

### 2. Criação do Módulo de Pipeline (`translate/pipeline.py`)
Encapsulará a lógica completa do ciclo de vida da tradução antes realizada em `runner.py`:
- `run_translation(ebook, provider, config, work_dir, on_event: Callable[[TranslationEvent], None], cancel_check: Callable[[], bool]) -> RunResult`
- Ela fará a extração do glossário, priming, inicialização do orquestrador de lotes e a gravação final do EPUB, notificando o andamento de cada fase via `on_event`.

### 3. Extração do Planejador (`translate/planner.py`)
Mover as funções `plan_book` e `cache_status` de `runner.py` para um planejador isolado. As assinaturas não dependerão de nenhuma classe do pacote `tui`.

### 4. Teste de Conexão Centralizado nos Provedores
A função `test_connection()` será consolidada na classe base do tradutor ou em `providers/discovery.py`. A tela `ConfigScreen` apenas invocará a interface de teste delegada.

## Risks / Trade-offs

- **[Risco] Concorrência e Conflito de Thread no Textual ao atualizar a UI**
  - *Mitigação*: Garantir que os callbacks passados ao pipeline NUNCA alterem widgets ou propriedades da tela diretamente. Eles devem exclusivamente usar `self.post_message(event)` para enfileirar as mensagens no loop principal da UI (que roda na thread principal de forma segura).
- **[Risco] Eventos enviados de forma assíncrona dificultando o cancelamento ordenado**
  - *Mitigação*: O cancelamento continuará usando uma checagem ativa por pull (`cancel_check: Callable[[], bool]`) para que o motor na thread secundária possa ler instantaneamente se o usuário pressionou a tecla de cancelar na TUI e interromper o envio de novos lotes de forma rápida.
