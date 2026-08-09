## Context

Ver `proposal.md` para a motivação. O sistema atual enfrenta gargalos de velocidade devido ao paralelismo travado em 4 conexões, lotes de 3.000 tokens com alta latência por requisição HTTP, descartes integrais de lote por falhas pontuais de tags HTML e timeouts longos.

## Goals / Non-Goals

**Goals:**
- Implementar um teto de concorrência global seguro (`MAX_GLOBAL_PARALLELISM = 20`) e calcular dinamicamente o máximo permitido para o usuário na interface TUI.
- Reduzir o tamanho do lote para LLMs para 10 a 15 itens por requisição (~1.000 a 1.200 tokens).
- Aceitar e armazenar no cache (`estado.json`) os blocos válidos de cada lote imediatamente, re-enfileirando individualmente apenas os blocos que apresentarem erros de formatação.
- Ajustar os parâmetros de resiliência de rede (timeout 45s, 3 retries, max_delay 15s) no adapter OpenAI-compatível.
- Integrar a opção de desativar Glossário/Guia de Estilo na tela de execução do e-book e persistir `priming.txt` no disco.
- Tratar título e rótulos do sumário como blocos normais no orquestrador.

**Non-Goals:**
- Mudar o protocolo de comunicação dos adaptadores de LLM ou adicionar novos provedores nesta alteração.
- Alterar o esquema de chaves no keyring ou o formato do `estado.json`.

## Decisions

### 1. Concorrência Tripla (`MAX_GLOBAL_PARALLELISM = 20`)
- **Decisão:** O paralelismo efetivo no orquestrador será calculado por `min(user_parallelism, provider_max_concurrency, 20)`. No `deepseek.py`, atualizaremos a concorrência declarada.
- **Alternativa Considerada:** Permitir paralelismo ilimitado configurado pelo usuário. Descartado devido ao risco de estouro de memória/sockets e congelamento da TUI.

### 2. Respeito ao `max_batch_items` no Orquestrador
- **Decisão:** No `orchestrator.py`, a chamada a `make_batches` para LLMs considerará tanto o limite de tokens quanto `max_batch_items` (10 a 15 itens por lote).
- **Alternativa Considerada:** Manter apenas o filtro por tokens. Descartado porque 3.000 tokens em parágrafos curtos geram arrays de 60+ itens, aumentando o tempo por chamada para 60s.

### 3. Aceitação Parcial de Blocos no Orquestrador
- **Decisão:** Ao receber o lote, iterar sobre os blocos. Os blocos com fidelidade de formatação e texto válido são gravados em `state.translations` e persistidos. Os blocos corrompidos são devolvidos à fila de pendências.
- **Alternativa Considerada:** Descarte integral do lote (tudo-ou-nada). Descartado pois causava retries custosos de 50 parágrafos por conta de 1 tag desalinhada.

### 4. Persistência de `priming.txt`
- **Decisão:** Salvar o resultado da passada de priming em `priming.txt` no diretório de trabalho do livro (`work_dir`). Se o arquivo existir, lê do disco sem chamar a API.

### 5. Inclusão de Título e Sumário na Fila Principal
- **Decisão:** Inserir os blocos de título e sumário antes de criar os lotes no `translate_book`, com IDs/kinds apropriados, removendo a necessidade de chamadas pós-processamento separadas no `pipeline.py`.

## Risks / Trade-offs

- **[Risco] Re-enfileiramento excessivo em falhas recorrentes** → *Mitigação:* Manter limite de tentativas por bloco individual no orquestrador para evitar loops infinitos caso um bloco falhe sistematicamente.
- **[Risco] Sobrecarga de rede com 20 threads** → *Mitigação:* `httpx` gerencia conexões no pool e o limite de 20 threads é seguro para sistemas operacionais desktop modernos.
