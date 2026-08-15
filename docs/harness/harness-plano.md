# Plano de Harness de Engenharia: tradutor-ebook

*(gerado pela skill `harness-setup` — documento de plano vivo; cada reauditoria adiciona uma nova seção datada abaixo, preservando o histórico de evolução do projeto)*

Baseado em "Harness Engineering for Coding Agent Users" e seu follow-up sobre sensores de manutenibilidade (Böckeler/Fowler).

---

## Diagnóstico Inicial de 15/08/2026 (Pré-Implementação)

### 1. Artefatos Já Consultados
*(o que já existia e evitou redescoberta do zero)*

- `docs/fundacao/fundacao.md`: Existente (gerado em 10/08/2026). Reutilizado: Domínio e problema (leitores de EPUB com BYOK LLM/tradução automática), 5 características arquitetônicas priorizadas (*Fidelidade de Markup*, *Segurança/Privacidade*, *Resiliência*, *Testabilidade/Manutenibilidade*, *Usabilidade/Portabilidade*), estilo Monolito Modular Hexagonal com particionamento *package-by-component*, stack (Python 3.12+, Textual, lxml, httpx, tiktoken, keyring, pydantic, hatch) e ADR-001 a ADR-005.
- `docs/arquitetura/arquitetura.html`: Existente. Reutilizadas: Regras de Acoplamento Hexagonal (isolamento estrito de `domain/` sem I/O nem dependências externas; `epub/` e `translate/` dependentes apenas de `domain/`; adapters isolados em `infra/`, `providers/` e `tui/`) e ADRs registrados (ADR-01 a ADR-06).
- `docs/specs/` e `docs/specs/rapidas/`: Em pleno uso ativo. Mudanças estruturais e rápidas são especificadas antes da codificação com critérios de aceite e Fitness Functions explícitas.
- `docs/reviews/*.md`: 16 relatórios de auditoria existentes da skill `code-review`. Padrão observado: zero bloqueadores arquiteturais históricos nos merges (forte aderência a regras de domínio), porém com necessidade recorrente de verificações de regressão de encoding, integridade de tags XML e tratamento atômico de arquivos no Windows.
- Skills já em uso no projeto: `fundacao-projeto`, `architecture-report`, `especificar-funcionalidade`, `modificacao-rapida`, `code-review`, `documentacao` e `openspec-*` cobrem formalmente os itens G4, G6, S7 e P4.

### 2. Contexto do Projeto
*(calibra o teto de investimento em harness — nunca pule esta etapa)*

| Pergunta | Resposta |
|---|---|
| Objetivo (pessoal, trabalho, open-source, produção crítica) | Open-source público com usuários reais (distribuição desktop/TUI). |
| Quantas pessoas usam/mantêm | 1 mantenedor com usuários externos utilizando as releases. |
| Já está em produção, com usuários reais? | Sim (versão estável v0.5.1 já publicada com executável Windows standalone e auto-update). |
| Tolerância a downtime/bugs | Baixa tolerância — o app precisa ser extremamente estável para não corromper livros ou gastar tokens indevidamente. |
| Autonomia do agente de IA (supervisionado, semi, autônomo) | Semi-autônomo supervisionado (o agente propõe planos, specs, código e revisões, com aprovação humana em PRs). |
| Testes do projeto são majoritariamente gerados por IA sem revisão humana extensa? | Sim, muitos testes foram gerados com assistência de IA e necessitam de validação semântica profunda. |
| Prazo/urgência | Prioridade moderada — aplicar melhorias essenciais antes das próximas grandes features. |

### 3. Tabela de Diagnóstico Inicial

Legenda: ✅ implementado | ⚠️ parcial | ❌ ausente. Nível: **Essencial** / **Recomendado** / **Provável over-engineering** (para este contexto).

| Item | Status | Nível | Fonte/Nota |
|---|---|---|---|
| G1 — Guia de convenções do projeto (AGENTS.md ou equivalente) | ✅ | Essencial | `AGENTS.md` e `GEMINI.md` definem fluxo de PR, commits convencionais e regras. |
| G2 — Glossário de domínio | ✅ | Recomendado | `docs/fundacao/fundacao.md` Seções 1 e 2 definem conceitos centrais e atores. |
| G3 — ADRs registrados | ✅ | Essencial | `docs/fundacao/fundacao.md` (ADR-001 a 005) e `docs/arquitetura/arquitetura.html` (ADR-01 a 06). |
| G4 — Skills/how-tos para tarefas recorrentes | ✅ | Recomendado | Conjunto de 13 skills em `.agent/skills/` cobrindo todo o ciclo de vida. |
| G5 — LSP/análise de código habilitada pro agente | ✅ | Recomendado | CodeGraph integrado com suporte a busca semântica e hops estruturais. |
| G6 — Spec antes de implementar | ✅ | Essencial | Coberto ativamente por `especificar-funcionalidade` e `modificacao-rapida`. |
| G7 — Template de módulo novo | ⚠️ | Recomendado | Arquitetura definida, mas sem templates/scaffold de novos provedores de tradução. |
| G8 — Docs de APIs externas | ⚠️ | Recomendado | Provedores implementados em `src/tradutor/providers/`, mas sem doc consolidada de contratos HTTP. |
| S1 — Linter no CI | ✅ | Essencial | `ruff check` e `ruff format --check` ativos no `.github/workflows/ci.yml`. |
| S2 — Checagem de tipos estrita (Type checking) | ❌ | Essencial | Type annotations presentes no código, mas sem `mypy`/`pyright` no CI ou scripts do hatch. |
| S3 — Testes com coverage gate | ✅ | Essencial | `pytest` + `coverage` com gate rígido de `>= 95%` (`tool.coverage.report.fail_under = 95`). |
| S4 — Pre-commit hooks | ⚠️ | Essencial | `.githooks/commit-msg` ativo para commits, mas sem hook local executando lint/format antes do commit. |
| S5 — Pipeline de CI completo | ✅ | Essencial | GitHub Actions com matriz Python 3.12/3.13, lint, coverage gate, commitizen check e gate agregador. |
| S6 — Fitness functions / regras de dependência | ⚠️ | Essencial | Auditado via agente no `code-review`, mas sem sensor computacional automatizado (`import-linter`). |
| S7 — Review agents (inferencial) | ✅ | Recomendado | Skill `code-review` audita conformidade arquitetural e specs antes do merge. |
| S8 — E2E para fluxos críticos | ⚠️ | Recomendado | Testes de integração cobrem pipeline e containers, mas falta E2E via Textual Pilot para a TUI. |
| S9 — Approved fixtures | ✅ | Recomendado | Fixtures de EPUBs sintéticos e trechos XHTML em `tests/` e testes de regressão de encoding. |
| S10 — Mutation testing | ❌ | Essencial | **Elevado a Essencial**: testes com alta geração por IA exigem validação de eficácia real de asserções. |
| S11 — Dependency scan | ❌ | Recomendado | Ausência de scanner automatizado de vulnerabilidades (`pip-audit` / Dependabot). |
| S12 — Dead code detection | ❌ | Recomendado | Sem ferramenta automatizada para detectar código/módulos órfãos (`vulture`). |
| S13 — Mecanismo de verificação forçada dos sensores | ⚠️ | Essencial | Bloqueio forçado garantido no CI do GitHub, mas parcialmente dependente de disciplina manual local. |
| O1 — Logging estruturado + request-id | ⚠️ | Recomendado | Eventos e sanitização na TUI e `estado.json`, mas sem logging de sessão com correlation ID. |
| O2 — Health check endpoint | ❌ | Provável over-engineering | Não aplicável: aplicativo desktop local/TUI sem servidor HTTP exposto. |
| O3 — Métricas de runtime | ⚠️ | Recomendado | Métricas de custo/tokens/tempo por sessão exibidas na TUI e cacheadas localmente. |
| O4 — SLOs com alertas | ❌ | Provável over-engineering | Não aplicável para cliente desktop distribuído sem infraestrutura em nuvem centralizada. |
| O5 — Tracing distribuído | ❌ | Provável over-engineering | Não aplicável: mono-processo desktop com chamadas assíncronas diretas a APIs externas. |
| O6 — Sensor contínuo → steering loop | ❌ | Recomendado | Não há sensor daemon em background durante o ciclo de edição. |
| P1 — Steering loop ativo | ⚠️ | Recomendado | Ciclo spec -> impl -> code-review funciona sob demanda por tarefa. |
| P2 — Revisão periódica do harness | ⚠️ | Recomendado | Skill `harness-setup` estabelece o diagnóstico e histórico incremental. |
| P3 — Mensagens de erro acionáveis | ⚠️ | Essencial | Mensagens de linters e testes são padrão; falta embutir feedback orientativo em fitness functions. |
| P4 — Topologias restritas / variedade limitada | ✅ | Essencial | Monolito modular hexagonal documentado e padronizado em `fundacao.md`. |
| P5 — Harness versionado | ✅ | Essencial | Documentado e versionado em `docs/harness/harness-plano.md`. |
| P6 — Histórico de sensores registrado | ⚠️ | Recomendado | Registrado via `docs/reviews/` e histórico de execuções do GitHub Actions. |

### 4. Itens Classificados como Provável Over-Engineering
*(apresentados com justificativa — o desenvolvedor decide, a IA não remove unilateralmente)*

- **O2 — Health check endpoint:** O `tradutor-ebook` é uma ferramenta desktop interativa executada sob demanda pelo usuário final em seu próprio computador, e não um daemon/microsserviço de longa duração que necessite de probe HTTP de liveness/readiness. O teste de conectividade já existe na TUI (`Testar Conexão`).
- **O4 — SLOs com alertas:** Não há backend central operando 24/7 com equipe de SRE. A estabilidade é garantida por testes locais, resiliência do orquestrador e relatório pós-execução na TUI.
- **O5 — Tracing distribuído:** O sistema opera em um único processo desktop com `asyncio`. Spans distribuídos (OpenTelemetry para múltiplos microsserviços) adicionariam complexidade desnecessária de dependências e overhead de rede sem ganho real.

---

## Reauditoria de 15/08/2026 (Pós-Implementação dos Guides & Sensors)

### 1. Evolução do Repositório e Artefatos Produzidos
*(auditoria dos componentes implementados na branch `feat/26-guides-sensors` via `docs/specs/harness-guides-sensors.md`)*

- **Type Checking Estrito (S2):** `hatch run typecheck` configurado com `mypy --strict` e executando com 100% de sucesso sobre 103 arquivos de código-fonte (`src/` e `tests/`). Stubs tipados adicionados via `lxml-stubs`.
- **Fitness Functions Hexagonais (S6):** `import-linter` e `tests/arch/test_architecture.py` validam contratos formais em tempo de execução e no CI, proibindo computacionalmente qualquer acoplamento indevido do `domain` com adapters ou do core com a TUI/CLI.
- **Pre-commit Hook Nativo (S4 / S13):** `.githooks/pre-commit` implementado em shell POSIX e ativado no `hatch run setup`, executando `ruff check`, `ruff format --check` e `mypy` automaticamente nos arquivos staged.
- **Mutation Testing (S10):** Runner `mutmut` configurado em `[tool.mutmut]` do `pyproject.toml` focando cirurgicamente nos 4 módulos críticos de integridade de tags e índices (`domain/protection.py`, `domain/quality.py`, `epub/segments.py`, `epub/index_rebuilder.py`).
- **Dependency Audit (S11):** `pip-audit` integrado ao `pyproject.toml` (`hatch run audit`) e ao pipeline de CI (`.github/workflows/ci.yml`), verificando CVEs em tempo de PR.
- **Dead Code Detection (S12):** `vulture` integrado ao `pyproject.toml` (`hatch run deadcode`) com whitelist de handlers reativos e callbacks da TUI (Textual).
- **Testes E2E com Textual Pilot (S8):** Suíte assíncrona implementada em `tests/tui/test_e2e_pilot.py` cobrindo 5 cenários completos de ponta a ponta (onboarding, configuração, teste de conexão assíncrono, cancelamento com retenção de estado e tradução integral).
- **Template de Novos Provedores (G7):** Guia `docs/guias/novo-provedor.md` publicado com especificações completas de contratos (`LLMTranslator`, `MachineTranslationProvider`), metadados `DESCRIPTION`, erros e rate limiting.
- **Auditoria de Conformidade (S7):** Relatório de `code-review` gerado em `docs/reviews/harness-guides-sensors.md` com veredito **PODE FINALIZAR SEM RESSALVAS** e cobertura branch global de **95%** (672 testes verdes).

---

### 2. Tabela de Diagnóstico Consolidada

Legenda: ✅ implementado | ⚠️ parcial | ❌ ausente. Nível: **Essencial** / **Recomendado** / **Provável over-engineering**.

| Item | Status | Nível | Situação Atual (Pós-Implementação) |
|---|---|---|---|
| G1 — Guia de convenções | ✅ | Essencial | `AGENTS.md` e `GEMINI.md` ativos e respeitados. |
| G2 — Glossário de domínio | ✅ | Recomendado | `docs/fundacao/fundacao.md` padronizado. |
| G3 — ADRs registrados | ✅ | Essencial | ADR-001 a ADR-006 registrados; ADR-007 proposto na spec. |
| G4 — Skills de tarefas recorrentes | ✅ | Recomendado | 13 skills especializadas em `.agent/skills/`. |
| G5 — LSP/análise de código | ✅ | Recomendado | CodeGraph integrado ao fluxo dos agentes. |
| G6 — Spec antes de implementar | ✅ | Essencial | `especificar-funcionalidade` e `modificacao-rapida` ativas. |
| G7 — Template de módulo novo | ✅ | Recomendado | **Evoluiu de ⚠️ para ✅**: `docs/guias/novo-provedor.md` criado. |
| G8 — Docs de APIs externas | ⚠️ | Recomendado | Contratos documentados em `docs/guias/novo-provedor.md`. |
| S1 — Linter no CI | ✅ | Essencial | `ruff check` e `ruff format --check` no CI e pre-commit. |
| S2 — Checagem de tipos estrita | ✅ | Essencial | **Evoluiu de ❌ para ✅**: `hatch run typecheck` (`mypy --strict`). |
| S3 — Testes com coverage gate | ✅ | Essencial | 672 testes automatizados mantendo `>= 95%` de cobertura. |
| S4 — Pre-commit hooks | ✅ | Essencial | **Evoluiu de ⚠️ para ✅**: `.githooks/pre-commit` ativo. |
| S5 — Pipeline de CI completo | ✅ | Essencial | GitHub Actions com lint, types, arch, audit, cov e gate agregador. |
| S6 — Fitness functions de arquitetura | ✅ | Essencial | **Evoluiu de ⚠️ para ✅**: `import-linter` e `tests/arch/test_architecture.py`. |
| S7 — Review agents (inferencial) | ✅ | Recomendado | Skill `code-review` com 17 relatórios consolidados em `docs/reviews/`. |
| S8 — E2E para fluxos críticos | ✅ | Recomendado | **Evoluiu de ⚠️ para ✅**: 5 testes E2E com Textual Pilot em `tests/tui/`. |
| S9 — Approved fixtures | ✅ | Recomendado | Fixtures de EPUBs e testes de regressão de encoding ativos. |
| S10 — Mutation testing | ✅ | Essencial | **Evoluiu de ❌ para ✅**: `[tool.mutmut]` ativo para os 4 módulos críticos. |
| S11 — Dependency scan | ✅ | Recomendado | **Evoluiu de ❌ para ✅**: `pip-audit` integrado ao Hatch e CI. |
| S12 — Dead code detection | ✅ | Recomendado | **Evoluiu de ❌ para ✅**: `vulture` integrado ao Hatch e CI. |
| S13 — Verificação forçada de sensores | ✅ | Essencial | **Evoluiu de ⚠️ para ✅**: Hook pre-commit local e CI gate obrigatório. |
| O1 — Logging estruturado + correlation ID | ⚠️ | Recomendado | Sanitização de dados ativa; logging rotativo por sessão ainda pendente. |
| O2 — Health check endpoint | ❌ | Provável over-engineering | Mantido como não aplicável (app desktop local). |
| O3 — Métricas de runtime | ⚠️ | Recomendado | Métricas de custo/tokens ativas na TUI. |
| O4 — SLOs com alertas | ❌ | Provável over-engineering | Mantido como não aplicável (sem backend em nuvem). |
| O5 — Tracing distribuído | ❌ | Provável over-engineering | Mantido como não aplicável (mono-processo desktop). |
| O6 — Sensor contínuo → steering loop | ⚠️ | Recomendado | Suportado pelo ciclo assistido via hooks locais e skills. |
| P1 — Steering loop ativo | ✅ | Recomendado | Ciclo spec -> impl -> review -> doc padronizado. |
| P2 — Revisão periódica do harness | ✅ | Recomendado | Skill `harness-setup` com reauditoria contínua versionada. |
| P3 — Mensagens de erro acionáveis | ✅ | Essencial | **Evoluiu de ⚠️ para ✅**: Pre-commit hook e sensores emitem feedback orientativo. |
| P4 — Topologias restritas | ✅ | Essencial | Monolito modular hexagonal mantido estritamente. |
| P5 — Harness versionado | ✅ | Essencial | Documentado em `docs/harness/harness-plano.md`. |
| P6 — Histórico de sensores registrado | ✅ | Recomendado | **Evoluiu de ⚠️ para ✅**: Relatórios `docs/reviews/` e esteira GitHub Actions. |

---

### 3. Backlog de Harness para Próximas Iterações

Com a conclusão dos 8 itens essenciais do harness de engenharia, os próximos refinamentos recomendados (quando demandados por novas fases do projeto) são:

#### Item 1: Logging Rotativo de Sessão com Correlation ID (O1)
- **Categoria de ferramenta:** Logging estruturado em arquivo local (`logging.handlers.RotatingFileHandler`).
- **Objetivo:** Facilitar diagnóstico e suporte para usuários finais no Windows sem poluir a interface TUI com logs técnicos.
- **Esforço estimado / Impacto:** Baixo / Médio.

#### Item 2: Telemetria e Histórico de Latência por Provedor na TUI (O3)
- **Categoria de ferramenta:** Coleta de métricas em memória com serialização em `estado.json`.
- **Objetivo:** Dar visibilidade na tela de relatório sobre latência média por bloco e tempo de resposta de cada provedor utilizado.
- **Esforço estimado / Impacto:** Baixo / Baixo.

#### Item 3: Atualização do Painel de Arquitetura (Consolidação do ADR-007)
- **Ação:** Executar a skill `architecture-report` para consolidar o **ADR-007: Adoção de Harness de Engenharia com Sensores Determinísticos e Guides Feedforward** e sincronizar o painel interativo `docs/arquitetura/arquitetura.html`.
- **Esforço estimado / Impacto:** Baixo / Alto.

---

## Histórico de Execução do Plano Original

- [x] **Item 1 (Type Checking Estrito):** Implementado e validado (`hatch run typecheck`).
- [x] **Item 2 (Fitness Functions de Arquitetura):** Implementado e validado (`hatch run arch-check` e `tests/arch/test_architecture.py`).
- [x] **Item 3 (Pre-commit Hook Local):** Implementado e automatizado (`.githooks/pre-commit` e `hatch run setup`).
- [x] **Item 4 (Mutation Testing):** Implementado e configurado (`[tool.mutmut]` para módulos críticos).
- [x] **Item 5 (Dependency Vulnerability Scan):** Implementado e validado no CI (`hatch run audit`).
- [x] **Item 6 (Dead Code Detection):** Implementado e validado (`hatch run deadcode`).
- [x] **Item 7 (Testes E2E de TUI com Textual Pilot):** Implementado com 5 suítes completas em `tests/tui/test_e2e_pilot.py`.
- [x] **Item 8 (Scaffolding / Template para Novos Provedores):** Implementado em `docs/guias/novo-provedor.md`.
