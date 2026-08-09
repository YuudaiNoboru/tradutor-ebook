## 1. Ajustes no Provider e Rede

- [ ] 1.1 Atualizar concorrência declarada do DeepSeek em `src/tradutor/providers/llm/deepseek.py`
- [ ] 1.2 Ajustar parâmetros de resiliência de rede (timeout 45s, max_retries 3, max_delay 15s) em `src/tradutor/providers/llm/openai_compat.py`

## 2. Otimização do Motor de Tradução e Lotes

- [ ] 2.1 Atualizar `make_batches` e a chamada no `orchestrator.py` para respeitar `max_batch_items` (10 a 15 itens) em LLMs
- [ ] 2.2 Atualizar o orquestrador para aplicar o limite de concorrência global `MAX_GLOBAL_PARALLELISM = 20`
- [ ] 2.3 Implementar a aceitação parcial e salvamento imediato de blocos válidos no cache, re-enfileirando apenas blocos corrompidos no `orchestrator.py`
- [ ] 2.4 Mover a tradução de título e rótulos do sumário para a fila principal de lotes do orquestrador no `pipeline.py`

## 3. Passadas Iniciais e Interface TUI

- [ ] 3.1 Implementar a persistência do resumo de tom em `priming.txt` no `pipeline.py` e `passadas.py`
- [ ] 3.2 Renomear "Priming" para "Guia de Estilo e Tom" nas mensagens de log e interface
- [ ] 3.3 Adicionar a opção `[X] Gerar Glossário e Guia de Estilo` na tela do e-book (para provedores LLM) e integrar ao pipeline
- [ ] 3.4 Atualizar a tela de configuração (`config.py`) para exibir o limite dinâmico de paralelismo `min(20, provider_max_concurrency)` e validar o input

## 4. Testes e Validação

- [ ] 4.1 Atualizar e adicionar testes unitários cobrindo o novo limite de lote, resiliência de rede e concorrência global
- [ ] 4.2 Executar suíte de validação (`hatch run lint`, `hatch run fmt-check`, `hatch run cov`)
