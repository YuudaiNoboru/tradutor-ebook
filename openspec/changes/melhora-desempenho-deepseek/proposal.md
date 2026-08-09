## Why

Com DeepSeek selecionado, a tradução fica extremamente lenta (ETA vivo de quase 5h em livro de ~295k tokens) e demora minutos para iniciar: o request não envia `max_tokens` e a API corta respostas grandes em 4.096 tokens, gerando retries silenciosos; glossário e priming rodam em sequência antes do primeiro lote; e a estimativa pré-voo (20s/lote fixos) não reflete a latência real de geração longa.

## What Changes

- Enviar `max_tokens` (default 8192) no body de `POST /chat/completions` do adapter OpenAI-compatível, evitando truncamento da resposta em lotes cheios.
- Reduzir o limite padrão de lote de 4000 para 3000 tokens de entrada, para que a saída esperada (fator de expansão ~1.2) caiba no teto de saída do modelo sem truncar.
- Executar as passadas de glossário e priming em paralelo (são independentes), reduzindo o tempo até o primeiro lote.
- Estimar o tempo pré-voo com latência declarada por provider (ex.: DeepSeek ~90s/lote) em vez de 20s fixos, alinhando estimativa e ETA real.
- Logar retries/backoffs do provider (429, 5xx, timeout, JSON inválido) mantendo a redação de segredos, para diagnóstico.

## Capabilities

### New Capabilities

(nenhuma)

### Modified Capabilities

- `llm-provider`: o adapter compatível com OpenAI passa a enviar `max_tokens` nas requisições e a registrar retries/backoffs de erros transitórios no log
- `translation-engine`: o limite padrão de lote muda de 4000 para 3000 tokens de entrada, e as passadas de glossário e priming passam a executar em paralelo quando ambas são suportadas
- `cost-control`: o tempo estimado pré-voo passa a usar a latência por lote declarada pelo provider em vez do valor fixo genérico

## Impact

- `src/tradutor/providers/openai_compat.py`: `max_tokens` no body, log de retries com redação
- `src/tradutor/providers/llm/deepseek.py`: capabilities com latência declarada e teto de saída
- `src/tradutor/domain/providers.py`: campos de latência/teto de saída nas capabilities
- `src/tradutor/translate/pipeline.py`: limite padrão de lote, paralelismo das passadas, latência por provider
- `src/tradutor/translate/planner.py`: limite padrão de lote e latência por provider na estimativa
- Testes: `tests/` de provider, batching, pipeline e estimativa; gate de cobertura >= 95% deve continuar verde
