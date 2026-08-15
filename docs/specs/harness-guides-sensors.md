# Especificação da Funcionalidade: Sistema Integrado de Harness de Engenharia (Guides & Sensors)

---

## 1. Entrada do Desenvolvedor: Mapeamento de Atores & Ações
*(fornecido pelo desenvolvedor e validado na Etapa 1)*

### Contexto / Objetivo Resumido
Implementar um sistema completo e robusto de **Harness de Engenharia** (*Guides* preventivos e *Sensors* determinísticos de feedback contínuo) no repositório `tradutor-ebook` (conforme diagnosticado e planejado no [`docs/harness/harness-plano.md`](file:///C:/Users/vasco/Documents/Software/tradutor-ebook/docs/harness/harness-plano.md)), blindando o projeto contra desvios arquiteturais, falhas de tipagem, testes ineficazes, vulnerabilidades de dependências, código morto e regressões na interface TUI.

### Papéis de Usuário Envolvidos
- **Desenvolvedor / Mantenedor:** Executa validações de qualidade locais unificadas via Hatch, conta com pre-commit hooks nativos para evitar retrabalho e tem à disposição templates claros para novos provedores.
- **Agente de IA (Coding Agent):** Recebe orientações preventivas (*guides*) e feedback de autocorreção determinístico e acionável (*sensors*) em tempo de desenvolvimento.
- **Leitor (Usuário Final do App):** Beneficiário indireto da alta estabilidade, preservação garantida da integridade do livro e ausência de regressões silenciosas.

---

### Ator: Desenvolvedor / Mantenedor
- **DEV-01:** Como desenvolvedor, quero rodar comandos unificados no Hatch (`hatch run typecheck`, `hatch run arch-check`, `hatch run mutate`, `hatch run audit`, `hatch run deadcode`) para validar a saúde do código localmente com facilidade.
- **DEV-02:** Como desenvolvedor, quero ter um hook local `pre-commit` instalado automaticamente via `hatch run setup` que impeça commits com erros de formatação, lint ou tipagem nos arquivos staged.
- **DEV-03:** Como desenvolvedor, quero ter testes E2E assíncronos que simulem a interface TUI completa (via Textual Pilot) para evitar regressões visuais e de navegação sem depender de testes manuais.
- **DEV-04:** Como desenvolvedor, quero um guia/template documentado para implementar novos provedores de tradução de forma padronizada e segura.

### Ator: Agente de IA (Coding Agent)
- **AI-01:** Como agente de IA, quero receber mensagens de erro determinísticas, acionáveis e explicativas ao violar uma regra de acoplamento hexagonal ou tipagem, sabendo exatamente onde e como corrigir o código.
- **AI-02:** Como agente de IA, quero ter sensores de teste de mutação para saber se os testes gerados possuem asserções eficazes e não apenas cobertura cosmética de linhas.

### Ator: Sistema (CI / Automações de Background)
- **SYS-01:** O sistema de CI deve executar a verificação estrita de tipos (`typecheck`) e falhar caso haja incompatibilidade ou ausência de anotações obrigatórias.
- **SYS-02:** O sistema de CI deve executar o linter de arquitetura (`arch-check`) e falhar imediatamente se qualquer módulo de `domain/` importar módulos de infraestrutura, UI, parser ou orquestração.
- **SYS-03:** O sistema de CI deve auditar vulnerabilidades conhecidas em dependências de terceiros (`pip-audit`) a cada Pull Request.
- **SYS-04:** O job `gate` no CI deve incluir todos os novos sensores determinísticos como pré-requisito de aprovação da esteira.

---

## 2. Análise Arquitetônica & Trade-offs
*(preenchido com base em Richards & Ford e aprovado na Etapa 2)*

### Características Arquitetônicas Críticas (-ilities)
- **Testabilidade & Verificação Semântica (Testability & Mutation Fitness):** Garantir que a suíte com gate de 95% de cobertura não seja apenas cosmética, mas semanticamente impenetrável contra mutações nos módulos vitais de integridade e proteção de markup.
- **Manutenibilidade & Corretude Estática (Maintainability & Static Typing):** Tipagem estrita completa em Python 3.12+ para evitar erros em tempo de execução causados por refatorações de IA ou interfaces assíncronas.
- **Integridade Estrutural & Acoplamento Hexagonal (Architecture Fitness & Decoupling):** Imposição computacional e determinística das fronteiras de camadas definidas no `docs/fundacao/fundacao.md` e `docs/arquitetura/arquitetura.html`.
- **Segurança da Cadeia de Suprimentos (Supply Chain Security):** Bloqueio proativo de pacotes com vulnerabilidades conhecidas (CVEs).

### Trade-offs Aceitos
> **Decisão de Trade-off 1: Mutation Testing Escopado vs. Execução Completa da Base.**
> - *Sacrifício:* O teste de mutação (`mutmut`) não é executado sobre 100% dos arquivos (como telas TUI ou scripts de CLI).
> - *Ganho:* O tempo de execução local (`hatch run mutate`) mantém-se entre 1 e 3 minutos em vez de dezenas de minutos, focando o esforço de mutação cirurgicamente nos 4 módulos onde a corrupção de dados seria inaceitável (`domain/protection.py`, `domain/quality.py`, `epub/segments.py`, `epub/index_rebuilder.py`).

> **Decisão de Trade-off 2: Hooks Git Nativos em `.githooks/` vs. Framework `pre-commit`.**
> - *Sacrifício:* O desenvolvedor precisa rodar `hatch run setup` uma vez ao clonar o repositório para ativar os hooks via `core.hooksPath`.
> - *Ganho:* Zero dependências externas no sistema, zero cache de múltiplos virtualenvs paralelos e reaproveitamento integral do fluxo já adotado no projeto para `.githooks/commit-msg`.

> **Decisão de Trade-off 3: Verificação Estrita de Tipos vs. Flexibilidade Dinâmica.**
> - *Sacrifício:* O código não aceita tipagem ambígua (`Any`) nem omissões de tipos de retorno; dependências sem stubs (como `ebooklib`) exigem isolamento de regras no `pyproject.toml`.
> - *Ganho:* Refatorações autônomas por agentes de IA tornam-se ordens de magnitude mais seguras contra erros sutis de `NoneType`, estruturas de dicionários e tipos assíncronos.

---

## 3. Estrutura Física & Módulos

### Mapeamento no Projeto Existente
```text
tradutor-ebook/
├── .github/
│   └── workflows/
│       └── ci.yml                   <-- [MODIFICADO: inclusão de typecheck, arch-check e audit no pipeline e gate]
├── .githooks/
│   ├── commit-msg                   <-- [EXISTENTE: validação de conventional commits]
│   └── pre-commit                   <-- [NOVO: hook nativo rodando ruff lint/format e mypy nos arquivos staged]
├── docs/
│   ├── guias/
│   │   └── novo-provedor.md         <-- [NOVO GUIA: template e contrato formal para criação de novos provedores]
│   ├── harness/
│   │   └── harness-plano.md         <-- [EXISTENTE: diagnóstico e roadmap de harness versionado]
│   └── specs/
│       └── harness-guides-sensors.md <-- [ESTA SPEC]
├── tests/
│   ├── arch/
│   │   ├── __init__.py              <-- [NOVO PACOTE]
│   │   └── test_architecture.py     <-- [NOVO: suite pytest rodando import-linter programaticamente com mensagens ricas]
│   └── tui/
│       └── test_e2e_pilot.py        <-- [NOVO: testes E2E simulando fluxos completos via Textual Pilot]
└── pyproject.toml                   <-- [MODIFICADO: dependências dev, scripts hatch e configs de mypy, importlinter, mutmut, vulture]
```

### Regras de Acoplamento & Limites
- **Camada 1 — `src/tradutor/domain`:** Isolamento puro. NUNCA pode importar de `epub`, `translate`, `infra`, `providers` ou `tui`.
- **Camada 2 — `src/tradutor/epub` e `src/tradutor/translate`:** Podem importar apenas de `domain` e bibliotecas utilitárias. NUNCA podem importar de `infra`, `providers` ou `tui`.
- **Camada 3 — `src/tradutor/infra`, `src/tradutor/providers`, `src/tradutor/tui`:** Adaptadores periféricos que implementam portas do domínio/orquestrador.
- **Sensor de Acoplamento:** Imposição via `import-linter` configurado no `pyproject.toml` ou `.importlinter` e executado em `hatch run arch-check` e `tests/arch/test_architecture.py`.

---

## 4. Fluxo de Execução & Casos de Borda

### Sequência Lógica

1. **[Ativação Inicial do Ambiente]:**
   - O desenvolvedor executa `hatch run setup`. O Git configura `core.hooksPath = .githooks`.

2. **[Fluxo de Desenvolvimento Local e Pre-commit]:**
   - Ao executar `git commit`, o hook `.githooks/pre-commit` é acionado pelo Git.
   - O hook detecta arquivos `.py` staged e executa:
     - `ruff check`
     - `ruff format --check`
     - `mypy` (nos arquivos alterados ou projeto)
   - Se houver falha, o commit é cancelado com mensagem acionável orientando a rodar `hatch run fmt` ou corrigir o tipo.
   - Em seguida, o hook `.githooks/commit-msg` valida a mensagem convencional.

3. **[Sensores Unificados no Hatch]:**
   - `hatch run typecheck`: executa `mypy src/ tests/` com `--strict` e plugin Pydantic.
   - `hatch run arch-check`: executa `lint-imports` validando as camadas hexagonais.
   - `hatch run mutate`: executa `mutmut run` nos 4 módulos críticos e imprime o relatório de mutantes mortos vs sobreviventes.
   - `hatch run audit`: executa `pip-audit` reportando CVEs em dependências.
   - `hatch run deadcode`: executa `vulture src/ tests/` identificando código morto com suporte a whitelist.

4. **[Esteira de Integração Contínua (CI)]:**
   - No GitHub Actions, os jobs de matriz executam `lint`, `fmt-check`, `typecheck`, `arch-check`, `cov` (com gate de 95%) e `audit`.
   - O job `gate` agrega todos os resultados e bloqueia o merge caso qualquer sensor falhe.

### Casos de Borda e Erros

- **Bibliotecas Sem Type Stubs (`ebooklib`, etc.):**
  - *Problema:* `mypy` emitiria erros `import-untyped` para pacotes legados sem anotações de tipo no PyPI.
  - *Tratamento:* Configurar `[[tool.mypy.overrides]]` no `pyproject.toml` especificamente para esses módulos com `ignore_missing_imports = true`, proibindo `ignore_missing_imports` global.
- **Callbacks e Propriedades Reativas da TUI (Textual) no Dead Code Detector:**
  - *Problema:* O `vulture` pode sinalizar métodos de ação da TUI (ex: `action_cancel`, `watch_progress`) como código morto por serem chamados dinamicamente via reflexão pelo framework Textual.
  - *Tratamento:* Criar arquivo de whitelist (`vulture_whitelist.py` ou comentários `# type: ignore` / flags de confiança) ignorando métodos prefixados com `action_`, `watch_`, `on_` e `compose`.
- **Compatibilidade Multiplataforma dos Hooks Git (Windows vs POSIX):**
  - *Problema:* O desenvolvedor está no Windows (PowerShell / Git Bash) e o CI roda em Ubuntu. Hooks `.githooks/` devem ser portáveis.
  - *Tratamento:* O script `.githooks/pre-commit` deve ser escrito em shell POSIX padrão (`#!/bin/sh`), executável de forma idêntica pelo Git for Windows (que embute o interpretador `sh`) e por ambientes Linux/macOS.
- **Timeouts e Falso-positivos no Mutation Testing:**
  - *Problema:* Mutantes que introduzem loops infinitos (`while True`) poderiam travar o runner.
  - *Tratamento:* Configuração de timeout explícito por teste no `mutmut` e isolamento dos testes rápidos unitários nos módulos de `protection`, `quality`, `segments` e `index_rebuilder`.

---

## 5. Proposta de ADR — Registro de Decisão Arquitetônica

### ADR-007: Adoção de Harness de Engenharia com Sensores Determinísticos e Guides Feedforward

- **Status:** Proposto (a ser consolidado pós-implementação).
- **Contexto:** O projeto conta com desenvolvimento acelerado por agentes de IA e múltiplos colaboradores, necessitando de salvaguardas que impeçam regressões de tipagem, desvios na Arquitetura Hexagonal, testes com asserções ineficazes e dependências vulneráveis.
- **Decisão:**
  1. Adotar `mypy` com tipagem estrita no Hatch e CI.
  2. Impor as fronteiras de dependência da Arquitetura Hexagonal via `import-linter`.
  3. Adotar testes de mutação via `mutmut` nos módulos críticos de integridade de markup e domínio.
  4. Adotar hook Git nativo `pre-commit` automatizado via `hatch run setup`.
  5. Integrar `pip-audit` e `vulture` como sensores de segurança e manutenibilidade.
  6. Estabelecer guia declarativo para novos provedores em `docs/guias/novo-provedor.md`.
- **Consequências:**
  - *Positivas:* Blindagem automática da arquitetura; agentes de IA recebem feedback determinístico e autocorretivo antes do commit e no CI; maior confiança semântica na suíte de testes; zero complexidade de ferramentas externas desnecessárias.
  - *Negativas:* Pequeno incremento no tempo do CI (~30s a 1min) e necessidade de manter anotações de tipos rigorosas em todo código novo.

---

## 6. Funções de Aptidão (Fitness Functions) & Critérios de Aceite

- [x] **FF-01 (Static Type Safety):** `hatch run typecheck` executa sem erros em `src/tradutor/` e `tests/` com zero warnings não autorizados.
- [x] **FF-02 (Hexagonal Architecture Fitness):** `hatch run arch-check` valida com sucesso que `src/tradutor/domain` não importa nenhum outro módulo interno e que a hierarquia de camadas é 100% respeitada.
- [x] **FF-03 (Mutation Verification):** `hatch run mutate` executa nos módulos `domain/protection.py`, `domain/quality.py`, `epub/segments.py` e `epub/index_rebuilder.py` alcançando score de mutação satisfatório (zero mutantes sobreviventes nos fluxos principais de proteção de tags e âncoras).
- [x] **FF-04 (Pre-commit Blocker):** O hook `.githooks/pre-commit` bloqueia com sucesso commits locais contendo erros de lint (`ruff`) ou tipos (`mypy`).
- [x] **FF-05 (Dependency Audit):** `hatch run audit` executa com sucesso o `pip-audit` garantindo zero vulnerabilidades conhecidas no grafo de dependências.
- [x] **FF-06 (Dead Code Detection):** `hatch run deadcode` executa sem falsos positivos reportando zero código morto em `src/tradutor/`.
- [x] **FF-07 (TUI E2E Coverage):** Pelo menos 3 testes E2E assíncronos usando Textual `Pilot` passam com sucesso simulando os fluxos de tela do aplicativo.
- [x] **FF-08 (Provider Guide):** O documento `docs/guias/novo-provedor.md` existe, é claro e descreve detalhadamente o contrato da classe base `TranslationProvider` e o passo a passo de scaffold.
- [x] **FF-09 (CI Gate Aggregator):** O pipeline `.github/workflows/ci.yml` inclui os novos checks no job `gate` e passa 100% verde na matriz de execução.
- [x] **FF-10 (Gate de Cobertura Global):** A cobertura total de código do repositório permanece `>= 95%` (`hatch run cov`).

---

## 7. Reconciliação Pós-Implementação

- **Status da Implementação:** Concluída com 100% de conformidade com a especificação técnica original e critérios de aceite.
- **Relatório de Auditoria:** [`docs/reviews/harness-guides-sensors.md`](file:///C:/Users/vasco/Documents/Software/tradutor-ebook/docs/reviews/harness-guides-sensors.md) (Veredito: *Pode Finalizar sem Ressalvas*).
- **Resultados dos Sensores:**
  - `hatch run typecheck` (`mypy --strict`): 103 arquivos validados com 0 erros.
  - `hatch run arch-check` (`import-linter` + `tests/arch/test_architecture.py`): Contratos hexagonais 100% mantidos.
  - `hatch run audit` (`pip-audit`): Zero vulnerabilidades de segurança.
  - `hatch run deadcode` (`vulture`): Zero código morto em `src/tradutor/`.
  - `hatch run cov`: 672 testes passando com **95%** de cobertura global.
  - Testes E2E: 5 cenários assíncronos com Textual Pilot em `tests/tui/test_e2e_pilot.py`.
- **Artefatos Entregues:**
  - [`.githooks/pre-commit`](file:///C:/Users/vasco/Documents/Software/tradutor-ebook/.githooks/pre-commit)
  - [`docs/guias/novo-provedor.md`](file:///C:/Users/vasco/Documents/Software/tradutor-ebook/docs/guias/novo-provedor.md)
  - [`docs/harness/harness-plano.md`](file:///C:/Users/vasco/Documents/Software/tradutor-ebook/docs/harness/harness-plano.md)
  - [`tests/arch/test_architecture.py`](file:///C:/Users/vasco/Documents/Software/tradutor-ebook/tests/arch/test_architecture.py)
  - [`tests/tui/test_e2e_pilot.py`](file:///C:/Users/vasco/Documents/Software/tradutor-ebook/tests/tui/test_e2e_pilot.py)

