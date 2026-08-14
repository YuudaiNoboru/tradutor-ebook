# Modificação Rápida: Cancelamento imediato de tradução

*(preenchido em conjunto por desenvolvedor e IA — sem debate de trade-offs, sem ADR)*

## O que muda
Ao solicitar o cancelamento da tradução (via clique no botão "Cancelar" ou atalho Ctrl+C na tela de progresso):
1. A interface (`ProgressScreen`) responde instantaneamente: cancela o worker de tradução em background, desanexa handlers de log e transiciona imediatamente para a tela de estimativa (`EstimateScreen`) com o aviso `"Tradução cancelada; o progresso concluído ficou salvo para retomada."`.
2. O orquestrador de tradução (`translate_book` em `orchestrator.py`) interrompe a execução sem esperar o término de requisições HTTP paralelas em voo, efetuando `shutdown(wait=False, cancel_futures=True)` no pool de threads e levantando `TranslationCancelled` imediatamente.
3. O pipeline de tradução (`run_translation` em `pipeline.py`) verifica a flag de cancelamento antes e entre as passadas de qualidade (glossário e análise de estilo/tom).
4. O progresso concluído até o momento do cancelamento continua preservado em `estado.json` de forma atômica, enquanto o lote em execução no momento do cancelamento é descartado com segurança sem corromper o estado ou causar corridas na retomada.

## Por que
Anteriormente, o sistema realizava um "cancelamento ordenado (graceful drain)", mantendo a tela bloqueada com a mensagem `"cancelamento solicitado; encerrando apos o lote atual..."` enquanto aguardava todas as requisições HTTP em voo terminarem (o que podia levar até dezenas de segundos dependendo da latência do provedor e retries). O usuário espera resposta imediata ao solicitar o cancelamento.

## Arquivos afetados
- `src/tradutor/translate/orchestrator.py` — abortar o loop de lotes imediatamente ao detectar cancelamento, disparando `pool.shutdown(wait=False, cancel_futures=True)`.
- `src/tradutor/translate/pipeline.py` — verificar `cancel_check()` antes e entre passadas de qualidade.
- `src/tradutor/tui/screens/progress.py` — transição imediata para `EstimateScreen` no `action_cancel`, cancelando workers e ignorando callbacks tardios do worker cancelado.
- `tests/translate/test_orchestrator.py` — testar abort imediato sem bloqueio de threads pendentes.
- `tests/tui/test_runner.py` — verificar cancelamento no pipeline.
- `tests/tui/test_app_flows.py` — atualizar testes de fluxo de TUI para validar retorno imediato à `EstimateScreen`.

## Risco de Regressão
Médio — toca o ciclo de vida do worker de tradução, encerramento de threads no orquestrador e controle de telas na TUI.

## Precisa de teste novo?
Sim: testes cobrindo o cancelamento imediato sem espera de requisições lentas em voo, a preservação do estado anterior e a retomada limpa em seguida.

---

## ⚠️ Trava de Escalonamento

- Introduz um Ator/papel de usuário novo? não
- Cria ou muda uma regra de acoplamento entre componentes já registrada no `arquitetura.html`? não
- Contraria ou exige revisar um ADR aprovado? não
- Muda comportamento observável de forma que mereça uma decisão arquitetural registrada? não
