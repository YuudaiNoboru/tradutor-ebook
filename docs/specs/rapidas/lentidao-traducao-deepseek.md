# Modificação Rápida: Lentidão na tradução com DeepSeek

*(preenchido em conjunto por desenvolvedor e IA — sem debate de trade-offs, sem ADR)*

## O que muda

1. Enviar `max_tokens` (8192) no body do `POST /chat/completions` do provider
   OpenAI-compatível, eliminando o truncamento da resposta em 4096 tokens
   (default da DeepSeek) em lotes cheios e os retries silenciosos que o seguem.
2. Reduzir o lote padrão de 4000 para 3000 tokens de entrada, para que a saída
   esperada (fator de expansão ~1.2 → ~3600 tokens) caiba com folga no limite
   de saída do modelo.
3. Executar as passadas de glossário e priming em paralelo (são independentes),
   reduzindo o tempo de início da tradução.
4. Estimar o tempo pré-voo com latência por provider/modelo (ex.: DeepSeek
   ~90s/lote) em vez de 20s fixos, alinhando a estimativa com a realidade.
5. Logar retries/backoffs do provider (429, 5xx, timeout, JSON inválido) para
   diagnóstico sem quebrar a redação de segredos.

## Por que

Bug reportado: com DeepSeek selecionado, a tradução é muito lenta (ETA vivo de
quase 5h no livro FAS.epub — 39 capítulos, 4866 blocos, 75 lotes) e demora
vários minutos para iniciar. O request não envia `max_tokens`, então a DeepSeek
corta a saída em 4096 tokens; lotes de 4000 tokens de entrada geram ~4800 de
saída → JSON truncado → retries internos invisíveis com backoff de até 60s.
As passadas iniciais (glossário 20k chars + priming 12k chars) rodam
sequenciais antes do primeiro lote, sem feedback de ETA. A estimativa pré-voo
de 20s/lote é otimista demais e o paralelismo efetivo (4) diverge do
configurado (6).

## Arquivos afetados

- `src/tradutor/providers/openai_compat.py` (max_tokens no body, log de retries)
- `src/tradutor/translate/pipeline.py` (lote padrão, paralelizar passadas, latência)
- `src/tradutor/translate/planner.py` (lote padrão, latência por provider)
- `src/tradutor/domain/providers.py` (latência por provider nas capabilities)
- `src/tradutor/providers/llm/deepseek.py` (capabilities com latência/max_tokens)

## Risco de Regressão

Médio — mexe no fluxo quente de tradução (request, lotes, passadas) e na
estimativa. Mitigação: mudanças pequenas e localizadas; testes existentes de
batching/orquestrador/estimativa precisam rodar; max_tokens é opcional e
ignorado por APIs que não o suportam.

## Precisa de teste novo?

Sim:
- teste de que o body do request inclui `max_tokens` quando configurado;
- teste de que glossário e priming rodam em paralelo (sem deadlock, ambas
  executam);
- teste da estimativa com latência por provider;
- testes existentes de `make_batches` atualizados para o novo limite padrão.

---

## ⚠️ Trava de Escalonamento
*(a IA preenche isto antes de finalizar — se qualquer resposta for "sim", PARE e sugira migrar para o fluxo completo de `especificar-funcionalidade`, com debate e modelo.md)*

- Introduz um Ator/papel de usuário novo? **não**
- Cria ou muda uma regra de acoplamento entre componentes já registrada no `arquitetura.html`? **não**
- Contraria ou exige revisar um ADR aprovado? **não**
- Muda comportamento observável de forma que mereça uma decisão arquitetural registrada? **não**
