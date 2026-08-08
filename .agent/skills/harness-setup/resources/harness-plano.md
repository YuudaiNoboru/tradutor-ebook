# Plano de Harness de Engenharia: <NOME_DO_PROJETO>

*(gerado pela skill `harness-setup` — documento de plano apenas; a implementação de cada item acontece depois, via `especificar-funcionalidade`/`modificacao-rapida` + OpenSpec)*

Baseado em "Harness Engineering for Coding Agent Users" e seu follow-up sobre sensores de manutenibilidade (Böckeler/Fowler).

---

## Diagnóstico de <DATA>
*(cada reauditoria adiciona uma nova seção datada abaixo desta — não sobrescreva diagnósticos anteriores, para dar visibilidade de tendência ao longo do tempo)*

### 1. Artefatos Já Consultados
*(o que já existia e evitou redescoberta do zero)*

- `fundacao.md`: <existe? o que foi reaproveitado — características priorizadas, estilo, stack, ADRs>
- `arquitetura.html`: <existe? Regras de Acoplamento e ADRs reaproveitados>
- `specs/` e `specs/rapidas/`: <spec-before-code já em uso?>
- `reviews/*.md`: <padrões recorrentes de Bloqueador/Atenção encontrados, com contagem>
- Skills já em uso no projeto: <especificar-funcionalidade, modificacao-rapida, code-review, architecture-report, fundacao-projeto — quais já cobrem parte do harness>

### 2. Contexto do Projeto
*(calibra o teto de investimento em harness — nunca pule esta etapa)*

| Pergunta | Resposta |
|---|---|
| Objetivo (pessoal, trabalho, open-source, produção crítica) | |
| Quantas pessoas usam/mantêm | |
| Já está em produção, com usuários reais? | |
| Tolerância a downtime/bugs | |
| Autonomia do agente de IA (supervisionado, semi, autônomo) | |
| Testes do projeto são majoritariamente gerados por IA sem revisão humana extensa? | |
| Prazo/urgência | |

### 3. Tabela de Diagnóstico

Legenda: ✅ implementado | ⚠️ parcial | ❌ ausente. Nível: Essencial / Recomendado / Provável over-engineering (para este contexto).

| Item | Status | Nível | Fonte/Nota |
|---|---|---|---|
| G1 — Guia de convenções do projeto (AGENTS.md ou equivalente) | | | |
| G2 — Glossário de domínio | | | *(checar fundacao.md Seção 1 antes de perguntar do zero)* |
| G3 — ADRs registrados | | | *(checar fundacao.md Seção 8 + arquitetura.html)* |
| G4 — Skills/how-tos para tarefas recorrentes | | | |
| G5 — LSP/análise de código habilitada pro agente | | | |
| G6 — Spec antes de implementar | | | *(provavelmente ✅ se especificar-funcionalidade/modificacao-rapida já em uso)* |
| G7 — Template de módulo novo | | | |
| G8 — Docs de APIs externas | | | |
| S1 — Linter no CI | | | |
| S2 — Checagem de tipos estrita (se a linguagem suportar) | | | |
| S3 — Testes com coverage gate | | | *(coverage alto não é o mesmo que teste efetivo — ver S10)* |
| S4 — Pre-commit hooks | | | |
| S5 — Pipeline de CI completo | | | |
| S6 — Fitness functions / regras de dependência | | | *(derive das Regras de Acoplamento já em arquitetura.html, quando existir)* |
| S7 — Review agents (inferencial) | | | *(provavelmente ✅/⚠️ se code-review já em uso — avaliar se roda automático ou só sob demanda)* |
| S8 — E2E para fluxos críticos | | | |
| S9 — Approved fixtures | | | |
| S10 — Mutation testing | | | *(subir prioridade se testes são gerados por IA sem revisão — ver Seção 2)* |
| S11 — Dependency scan | | | |
| S12 — Dead code detection | | | |
| S13 — Mecanismo de verificação forçada dos sensores | | | *(guia sozinho é pouco confiável — ver Seção 5, campo "Mecanismo de Verificação")* |
| O1 — Logging estruturado + request-id | | | |
| O2 — Health check endpoint | | | |
| O3 — Métricas de runtime | | | |
| O4 — SLOs com alertas | | | |
| O5 — Tracing distribuído | | | |
| O6 — Sensor contínuo → steering loop | | | |
| P1 — Steering loop ativo | | | |
| P2 — Revisão periódica do harness | | | |
| P3 — Mensagens de erro acionáveis (orientação de autocorreção embutida) | | | |
| P4 — Topologias restritas / variedade limitada | | | |
| P5 — Harness versionado (este documento no controle de versão) | | | |
| P6 — Histórico de sensores registrado (para medir efetividade ao longo do tempo) | | | |

### 4. Itens Classificados como Provável Over-Engineering
*(apresentados com justificativa — o desenvolvedor decide, a IA não remove unilateralmente)*

- <item> — <por quê, neste contexto específico, o custo supera o benefício>

---

## Plano Priorizado

*(ordem por impacto/esforço — regra base: CI com lint/type/test → pre-commit → coverage gate → logging+health check → fitness functions → dependency scan+dead code → E2E/approved fixtures → métricas+SLOs → mutation testing → mensagens acionáveis → template de harness → tracing+sensor contínuo. Itens com evidência recorrente em `reviews/*.md` sobem de prioridade, citando a contagem de ocorrências.)*

### Item <N>: <nome>
- **Categoria de ferramenta:** <ex: "linter", "regras de dependência" — nunca uma ferramenta específica; ver resources/exemplos-ferramentas.md>
- **Objetivo:** <o que este item regula — maintainability / architecture fitness / behaviour>
- **Orientação de autocorreção a embutir:** <se aplicável — o que a mensagem do sensor deve dizer ao agente além de "falhou", para ele saber como corrigir>
- **Válvula de escape graduada:** <se for regra de threshold — sob quais condições o agente pode ajustar o limite em vez de bloquear, e como isso fica visível/revisável>
- **Mecanismo de verificação forçada:** <guia / hook pós-edição / git pre-commit / ferramenta custom — qual, e por quê>
- **Critério de aceite:** <como confirmar depois que foi implementado corretamente — quem valida isso é o desenvolvedor ou o code-review, não esta skill>
- **Esforço estimado / Impacto:** <Baixo/Médio/Alto>

*(repetir bloco por item aprovado)*

---

## Próximos Passos
- Itens pequenos (ex: "ligar linter no CI") → `modificacao-rapida` + OpenSpec.
- Itens estruturais (ex: "montar sensor contínuo com dashboard") → `especificar-funcionalidade` + OpenSpec.
- Depois de cada item implementado, `code-review` audita normalmente; se o item tocar componentes documentados, o lembrete de atualizar `arquitetura.html` do próprio `code-review` já cobre isso.
- Este documento não é reescrito do zero em reauditorias futuras — uma nova seção "Diagnóstico de <data>" é adicionada acima, preservando o histórico.
