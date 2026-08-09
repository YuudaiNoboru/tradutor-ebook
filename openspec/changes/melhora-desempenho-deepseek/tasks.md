## 1. Adapter OpenAI-compatível (spec: llm-provider)

- [x] 1.1 Adicionar `max_output_tokens: int | None = 8192` ao construtor de `OpenAICompatProvider` e incluir `max_tokens` no body de `_chat` somente quando não for `None`
- [x] 1.2 Registrar no log (com `logging.getLogger` e redação) o motivo, a tentativa e o backoff de cada retry em `OpenAICompatProvider.translate`, sem expor a chave
- [x] 1.3 Atualizar `tests/test_openai_compat.py`: body inclui `max_tokens` com o valor padrão, body omite `max_tokens` quando `None`, e retry transiente gera entrada de log sem segredo
- [x] 1.4 Atualizar o teste de contrato modular (capabilities da DeepSeek) se necessário em `tests/test_modular_contracts.py`

## 2. Capabilities do provider (spec: llm-provider, cost-control)

- [x] 2.1 Adicionar `latency_seconds: float | None` e o teto de saída (`max_output_tokens`) a `ProviderCapabilities` em `src/tradutor/domain/providers.py`
- [x] 2.2 Declarar na DeepSeek (`src/tradutor/providers/llm/deepseek.py` e capability padrão de `openai_compat.py`): teto de saída 8192 e `latency_seconds = 90.0`
- [x] 2.3 Expor função em `src/tradutor/providers/__init__.py` que devolve as capabilities de um provider selecionado sem instanciá-lo (para o planner)
- [x] 2.4 Testes das novas fields/defaults em `tests/test_modular_contracts.py` e `tests/test_openai_compat.py`

## 3. Lote padrão de 3000 tokens (spec: translation-engine)

- [x] 3.1 Reduzir `DEFAULT_MAX_TOKENS` de 4000 para 3000 em `src/tradutor/translate/pipeline.py` e `src/tradutor/translate/planner.py`
- [x] 3.2 Atualizar/ajustar testes de `make_batches` em `tests/test_batching.py` e os valores esperados de contagem de lotes no planejador (planner) e na tela de estimativa, se referenciarem 4000

## 4. Passadas iniciais em paralelo (spec: translation-engine)

- [x] 4.1 Em `run_translation` (`src/tradutor/translate/pipeline.py`), executar glossário e priming em `ThreadPoolExecutor(max_workers=2)` quando ambas as passadas forem suportadas e não houver glossário salvo; falha de uma não aborta a outra (avisos existentes mantidos) e as threads são juntadas antes de prosseguir
- [x] 4.2 Testes em `tests/test_passadas.py`/`tests/test_modular_orchestration.py`: ambas executam em paralelo (glossário salvo, priming executado; falha isolada do glossário não impede o priming e vice-versa)

## 5. Estimativa com latência por provider (spec: cost-control)

- [x] 5.1 Em `plan_book` (`src/tradutor/translate/planner.py`), usar `latency_seconds` das capabilities do provider selecionado na estimativa de tempo (LLM), com fallback para 20.0 quando não declarada
- [x] 5.2 Testes em `tests/test_cost.py`/testes do planner: estimativa usa latência declarada (ex.: DeepSeek 90s) e mantém 20.0 sem declaração

## 6. Validação final

- [x] 6.1 Rodar `hatch run lint`, `hatch run fmt-check` e `hatch run cov` (gate >= 95%) e deixar tudo verde
- [ ] 6.2 Conferir manualmente no TUI com DeepSeek: estimativa pré-voo com tempo realista e ETA vivo coerente
