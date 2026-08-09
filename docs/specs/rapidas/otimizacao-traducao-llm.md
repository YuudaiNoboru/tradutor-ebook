# Modificação Rápida: Otimização de Desempenho e Resiliência na Tradução via LLM (DeepSeek)

*(preenchido em conjunto por desenvolvedor e IA — sem debate de trade-offs, sem ADR)*

## O que muda
1. **Concorrência e Paralelismo:** Define um teto global máximo de 20 worker threads (`MAX_GLOBAL_PARALLELISM = 20`) e atualiza a capacidade do provider DeepSeek (`deepseek.py`). Na interface TUI, exibe o limite dinâmico de paralelismo `min(20, provider_max_concurrency)` com dica explicativa e validação.
2. **Lotes Menores:** Faz o `orchestrator.py` respeitar o limite de itens por lote (`max_batch_items = 10 a 15`, ~1.000 a 1.200 tokens) também para LLMs.
3. **Preservação de Formatação & Re-enfileiramento Seletivo:** Salva blocos válidos no cache (`estado.json`) imediatamente e re-enfileira apenas os blocos específicos que falharem no teste de fidelidade de formatação/tags.
4. **Passadas Iniciais (Glossário e Guia de Estilo):** Move a opção `[X] Gerar Glossário e Guia de Estilo` para a tela do e-book (exibida apenas para LLMs), renomeia "Priming" para "Guia de Estilo" nos logs/interface e persiste `priming.txt` no disco junto com `glossario.json`.
5. **Rede e Timeouts:** Ajusta no `openai_compat.py` o timeout HTTP para 45s, número de retries para 3 e max_delay para 15s.
6. **Título e Sumário:** Trata o título e os rótulos do sumário como blocos de texto normais na fila principal do orquestrador.

## Por que
A tradução com DeepSeek/LLMs apresentava tempo excessivo de execução devido ao paralelismo travado em 4, lotes gigantescos (3.000 tokens) com alta latência por resposta, descarte integral de lotes por pequenas divergências de tag HTML, timeouts longos (180s) e chamadas sequenciais bloqueantes pós-tradução.

## Arquivos afetados
- `src/tradutor/infra/config.py`
- `src/tradutor/providers/llm/deepseek.py`
- `src/tradutor/providers/llm/openai_compat.py`
- `src/tradutor/translate/orchestrator.py`
- `src/tradutor/translate/pipeline.py`
- `src/tradutor/translate/passadas.py`
- `src/tradutor/tui/screens/config.py`
- `src/tradutor/tui/screens/progress.py`

## Risco de Regressão
Baixo — As mudanças ajustam parâmetros de concorrência, dimensionamento de lote e re-enfileiramento mantendo os contratos das portas do domínio e a integridade do cache de retomada.

## Precisa de teste novo?
Sim, atualizar/adicionar testes unitários nos módulos de `orchestrator`, `pipeline`, `batching`, `openai_compat` e `config` para validar o teto de concorrência, o re-enfileiramento parcial e os novos limites de lote/timeout.

---

## ⚠️ Trava de Escalonamento
*(a IA preenche isto antes de finalizar — se qualquer resposta for "sim", PARE e sugira migrar para o fluxo completo de `especificar-funcionalidade`, com debate e modelo.md)*

- Introduz um Ator/papel de usuário novo? não
- Cria ou muda uma regra de acoplamento entre componentes já registrada no `docs/arquitetura/arquitetura.html`? não
- Contraria ou exige revisar um ADR aprovado? não
- Muda comportamento observável de forma que mereça uma decisão arquitetural registrada? não
