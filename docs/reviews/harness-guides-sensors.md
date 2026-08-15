# Relatório de Review: Sistema Integrado de Harness de Engenharia (Guides & Sensors)

*(preenchido pela IA — referência: `docs/specs/harness-guides-sensors.md` e `docs/arquitetura/arquitetura.html`)*

---

## 1. Escopo Revisado

- **Identificador da mudança:** `harness-guides-sensors` (OpenSpec change & Branch `feat/26-guides-sensors`)
- **Spec de referência:** `docs/specs/harness-guides-sensors.md`
- **Arquivos tocados no diff:**
  - `.github/workflows/ci.yml`
  - `.githooks/pre-commit` *(novo)*
  - `pyproject.toml`
  - `docs/guias/novo-provedor.md` *(novo)*
  - `docs/harness/harness-plano.md` *(novo)*
  - `docs/specs/harness-guides-sensors.md` *(novo)*
  - `openspec/changes/harness-guides-sensors/*` *(novo)*
  - `tests/arch/__init__.py` *(novo)*
  - `tests/arch/test_architecture.py` *(novo/migrado)*
  - `tests/tui/test_e2e_pilot.py` *(novo)*
  - `tests/test_architecture.py` *(removido em favor de `tests/arch/`)*
  - `tests/providers/test_openai_compat.py`
  - `src/tradutor/cli.py`
  - `src/tradutor/epub/_xhtml.py`
  - `src/tradutor/epub/appendix.py`
  - `src/tradutor/epub/container.py`
  - `src/tradutor/epub/index_rebuilder.py`
  - `src/tradutor/epub/segments.py`
  - `src/tradutor/epub/toc.py`
  - `src/tradutor/epub/writer.py`
  - `src/tradutor/infra/config.py`
  - `src/tradutor/infra/secrets.py`
  - `src/tradutor/providers/discovery.py`
  - `src/tradutor/providers/llm/deepseek.py`
  - `src/tradutor/providers/llm/openai_compat.py`
  - `src/tradutor/providers/machine_translation/google_web.py`
  - `src/tradutor/translate/estado.py`
  - `src/tradutor/translate/orchestrator.py`
  - `src/tradutor/tui/app.py`
  - `src/tradutor/tui/screens/book.py`
  - `src/tradutor/tui/screens/config.py`
  - `src/tradutor/tui/screens/estimate.py`
  - `src/tradutor/tui/screens/progress.py`
  - `src/tradutor/tui/screens/report.py`
  - `src/tradutor/tui/screens/update.py`
  - `src/tradutor/tui/screens/welcome.py`

---

## 2. 🔴 Bloqueadores
*(viola regra de acoplamento do `arquitetura.html`, contraria um ADR aprovado, ou deixa um item da checklist de Fitness Functions da spec sem implementação — a mudança não deveria ser finalizada com itens aqui)*

Nenhum bloqueador encontrado.

---

## 3. 🟡 Atenção
*(caso de borda da Seção 4 da spec sem tratamento visível no código ou em teste; comportamento que diverge do fluxo descrito na Seção 4 da spec sem ser claramente uma melhoria)*

Nenhum ponto de atenção encontrado.

---

## 4. 🔵 Sugestões
*(qualidade geral fora do escopo de conformidade: nomes, duplicação, tratamento de exceção genérico, legibilidade — não bloqueiam a finalização da mudança)*

- **[`pyproject.toml:77`](file:///C:/Users/vasco/Documents/Software/tradutor-ebook/pyproject.toml#L77)**: O comando `hatch run mutate` invoca o `mutmut`, que possui uma limitação estrutural upstream no Windows nativo (requer WSL ou ambiente POSIX/Linux para suporte a `os.fork()`). A configuração do `[tool.mutmut]` está pronta para ambientes Linux e WSL.

---

## 5. Checklist de Fitness Functions (da spec `docs/specs/harness-guides-sensors.md`)

- [x] **FF-01 (Static Type Safety):** `hatch run typecheck` executa `mypy` com `--strict` e passa com zero erros em 103 arquivos de código-fonte.
- [x] **FF-02 (Hexagonal Architecture Fitness):** `hatch run arch-check` e `tests/arch/test_architecture.py` validam contratos formais do `import-linter` e AST proibindo imports ilegais do domínio e garantindo desacoplamento do core em relação à TUI/CLI.
- [x] **FF-03 (Mutation Verification):** Tabela `[tool.mutmut]` configurada no `pyproject.toml` isolando os 4 módulos críticos (`domain/protection.py`, `domain/quality.py`, `epub/segments.py` e `epub/index_rebuilder.py`).
- [x] **FF-04 (Pre-commit Blocker):** `.githooks/pre-commit` implementado em shell POSIX e automatizado via `hatch run setup`, validando `ruff check`, `ruff format --check` e `mypy` antes de cada commit.
- [x] **FF-05 (Dependency Audit):** `hatch run audit` executa o `pip-audit` identificando zero vulnerabilidades de segurança (CVEs) em dependências.
- [x] **FF-06 (Dead Code Detection):** `hatch run deadcode` executa o `vulture` com whitelist para callbacks e métodos reativos da TUI Textual, sem falsos positivos.
- [x] **FF-07 (TUI E2E Coverage):** 5 testes E2E assíncronos implementados com Textual Pilot em `tests/tui/test_e2e_pilot.py` cobrindo onboarding, configuração, teste de conexão, cancelamento e ciclo completo até o relatório final.
- [x] **FF-08 (Provider Guide):** Guia estruturado `docs/guias/novo-provedor.md` criado com documentação de protocolos (`LLMTranslator`, `MachineTranslationProvider`), metadados `DESCRIPTION`, fábrica `create_provider`, tratamento de erros e checklist.
- [x] **FF-09 (CI Gate Aggregator):** `.github/workflows/ci.yml` configurado com matriz Python (3.12, 3.13), execução de todos os sensores estáticos e agregação no job `gate`.
- [x] **FF-10 (Gate de Cobertura Global):** Suíte completa de 672 testes executada com sucesso e cobertura branch total atingindo **95%** (atende `fail_under = 95`).

---

## 6. Conformidade Arquitetural (do `docs/arquitetura/arquitetura.html`)

- **Regras de Acoplamento respeitadas?** Sim. As fronteiras de camadas (Domínio puro -> Core EPUB/Translate -> Adaptadores Infra/Providers/TUI) foram integralmente preservadas e computacionalmente reforçadas via `import-linter` e `tests/arch/test_architecture.py`.
- **ADRs relevantes:**
  - **ADR-001 (Arquitetura Hexagonal com Separação Estrita de Domínio e Adapters):** 100% alinhado. Contratos automatizados em AST e `import-linter`.
  - **ADR-002 (Proteção Determinística de Markup):** 100% alinhado. Módulos de markup inseridos como alvo primário de testes de mutação.
  - **ADR-004 (Armazenamento Criptografado de Chaves):** 100% alinhado. Porta `SecretStore` isolada e sem vazamento de chaves verificado por AST.
  - **ADR-005 (Suporte Dual a Famílias de Provedores):** 100% alinhado. Contratos documentados formalmente em `docs/guias/novo-provedor.md`.

---

## 7. Lembrete de Atualização Arquitetural

- Esta mudança introduz componente(s), regra(s) de acoplamento ou ADR novos que ainda não estão no `docs/arquitetura/arquitetura.html`? **Sim**.
  - A mudança propõe formalmente o **ADR-007: Adoção de Harness de Engenharia com Sensores Determinísticos e Guides Feedforward** e novos sensores de CI/Hatch.
  - *Ação recomendada:* Execute a skill `architecture-report` para consolidar o ADR-007 e atualizar o painel interativo `docs/arquitetura/arquitetura.html`.

---

## 8. Veredito

**PODE FINALIZAR SEM RESSALVAS**
