## Context

See proposal.md - Why. Estado atual relevante: o adapter `OpenAICompatProvider` envia o body `{"model", "messages"}` sem `max_tokens` (openai_compat.py:163), a DeepSeek trunca a saída no default de 4.096 tokens e os retries são silenciosos; `DEFAULT_MAX_TOKENS = 4000` duplicado em `translate/pipeline.py` e `translate/planner.py`; as passadas de glossário e priming rodam em sequência em `run_translation`; a estimativa pré-voo usa `DEFAULT_LATENCY_SECONDS = 20.0` fixo em `domain/cost.py`; o paralelismo efetivo é limitado por `max_concurrency` das capabilities (`ProviderCapabilities`, domain/providers.py).

## Goals / Non-Goals

**Goals:**
- Eliminar truncamento de resposta e os retries silenciosos que ele causa em lotes cheios
- Reduzir o tempo até o primeiro lote (paralelismo das passadas)
- Estimativa pré-voo alinhada com a latência real de geração longa
- Retries visíveis no log para diagnóstico, sem expor segredos

**Non-Goals:**
- Não criar fila/agendamento, nem adaptação dinâmica de tamanho de lote por modelo
- Não mudar o protocolo, a interface `Translator` nem o formato do cache
- Não mexer no provider de tradução automática (Google Web)

## Decisions

### D1. `max_tokens` opcional no body do chat completions
Adicionar o parâmetro `max_output_tokens: int | None = 8192` ao construtor do `OpenAICompatProvider`; quando não for `None`, o body inclui `max_tokens`. A capability da DeepSeek declara o teto de saída; o default do adapter é 8192 por ser parâmetro aceito por todos os endpoints OpenAI-compatíveis usados (DeepSeek, OpenRouter, Groq, Ollama). Quem não quiser enviar desliga com `None`.
Alternativa rejeitada: continuar sem `max_tokens` e confiar no default do provedor — foi a causa do bug. Alternativa rejeitada: calcular o teto por modelo automaticamente — complexidade desnecessária para o projeto.

### D2. Lote padrão de 3000 tokens de entrada
Reduzir `DEFAULT_MAX_TOKENS` de 4000 para 3000 em `translate/pipeline.py` e `translate/planner.py` (constantes duplicadas hoje — manter a duplicação, o projeto já convive com ela; unificar ficaria em outro change). Com fator de expansão 1.2, a saída esperada (~3600) cabe no teto de 4096 da DeepSeek com folga.
Trade-off: ~33% mais lotes no livro de teste (75 → ~100), portanto mais requests; em troca elimina-se o cenário de truncamento que multiplicava o tempo por 5 (retries).

### D3. Latência por lote declarada nas capabilities
Adicionar `latency_seconds: float | None` em `ProviderCapabilities` (domain/providers.py); a DeepSeek declara `90.0` (geração de ~4800 tokens a ~20-30 tok/s + TTFT). `plan_book` consulta a capability do provider selecionado (função nova em `providers/__init__.py` que devolve as capabilities sem instanciar o provider) e usa `latency_seconds` dela; sem declaração, mantém 20.0.
Alternativa rejeitada: latência no `config.toml` — a spec define a latência como característica do provider, não da configuração do usuário.

### D4. Passadas de glossário e priming em paralelo
Em `run_translation`, quando `supports_glossary and supports_priming` e não há glossário salvo, executar as duas passadas em `ThreadPoolExecutor(max_workers=2)`. O provider já é usado concorrentemente pelo orquestrador (`ThreadPoolExecutor` de 4 no `translate_book`), então o adapter é seguro para uso concorrente. Falha de uma passada não aborta a outra (mantém o comportamento atual de aviso); as threads são juntadas antes de seguir. Com glossário já salvo, só o priming roda (sem mudança).

### D5. Log de retries no provider
No laço de tentativas de `OpenAICompatProvider.translate`, registrar via `logging.getLogger` o motivo do erro transitório, o número da tentativa e o backoff aplicado (ou `Retry-After`). As mensagens nunca contêm a chave (ela só vai no header, que não é logado); o pipeline continua recebendo apenas o erro final.

## Risks / Trade-offs

- [API que rejeita `max_tokens`] → Parâmetro opcional por provider (`None` desliga); os endpoints-alvo (DeepSeek, OpenRouter, Groq, Ollama) aceitam o campo
- [Paralelismo das passadas em provider concorrente] → O adapter já roda sob 4 threads no orquestrador; as passadas adicionam no máximo 2 threads momentâneas
- [Latência declarada desatualizada (90s) subestima/superestima] → Constante única nas capabilities da DeepSeek, fácil de ajustar; continua sendo estimativa (aviso já existe na UI)
- [Lote menor aumenta contagem de requests e TTFT total] → Compensado pela eliminação dos retries de truncamento; medir no ETA vivo após o deploy

## Migration Plan

Sem migração de dados nem de configuração: `max_tokens`, lote, latência e paralelismo das passadas são defaults internos. Rollback: reverter o PR (valores voltam a 4000/20.0/sequencial).

## Open Questions

Nenhuma — dúvidas de implementação (nome do campo, local da consulta de capabilities) não alteram spec, abordagem nem divisão de tarefas.
