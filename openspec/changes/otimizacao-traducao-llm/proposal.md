## Why

A tradução de e-books via LLM (especialmente com o provedor DeepSeek) atualmente apresenta alto tempo de resposta e travamentos perceptíveis para o usuário. Isso decorre de paralelismo travado em 4 conexões, lotes grandes de 3.000 tokens que exigem respostas JSON muito longas da API, descarte integral de lotes por divergências pontuais em tags HTML, timeouts longos (180s) e chamadas sequenciais bloqueantes de pós-processamento.

## What Changes

- **Concorrência e Paralelismo:** Define um teto máximo global de 20 worker threads (`MAX_GLOBAL_PARALLELISM = 20`) e atualiza a capacidade do provider DeepSeek. Na interface TUI, exibe o limite dinâmico de paralelismo `min(20, provider_max_concurrency)` com dica e validação de entrada.
- **Dimensionamento de Lotes para LLM:** Faz o orquestrador respeitar o limite de itens por lote (`max_batch_items = 10 a 15`, ~1.000 a 1.200 tokens) também para LLMs.
- **Preservação de Formatação & Re-enfileiramento Seletivo:** Salva blocos válidos no cache (`estado.json`) imediatamente e re-enfileira apenas os blocos específicos que falharem no teste de fidelidade de formatação/tags.
- **Passadas Iniciais (Glossário e Guia de Estilo):** Move a opção `[X] Gerar Glossário e Guia de Estilo` para a tela do e-book (exibida apenas para LLMs), renomeia "Priming" para "Guia de Estilo" nos logs/interface e persiste `priming.txt` no disco junto com `glossario.json`.
- **Rede e Timeouts:** Ajusta no `openai_compat.py` o timeout HTTP para 45s, número de retries para 3 e max_delay para 15s.
- **Título e Sumário:** Trata o título e os rótulos do sumário como blocos de texto normais na fila principal do orquestrador.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `translation-engine`: regras de dimensionamento de lote para LLMs, re-enfileiramento parcial de blocos com erro de formatação e inclusão de título/sumário na fila principal.
- `llm-provider`: ajustes de resiliência de rede (timeout de 45s, 3 retries, 15s max delay) e atualização da concorrência do DeepSeek.
- `tui-app`: exibição dinâmica do limite de paralelismo na configuração e inclusão da opção "Gerar Glossário e Guia de Estilo" na tela do e-book.

## Impact

- `src/tradutor/infra/config.py`: constantes e validação de limites de execução.
- `src/tradutor/providers/llm/deepseek.py` e `openai_compat.py`: parâmetros de rede e concorrência.
- `src/tradutor/translate/orchestrator.py` e `pipeline.py`: motor de lotes, validação e cache de estado.
- `src/tradutor/tui/screens/config.py` e `progress.py`: formulários e hints da TUI.
