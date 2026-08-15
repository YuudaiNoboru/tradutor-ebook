# Relatório de Review: Sistemática de Instalação e Atualização Windows

*(preenchido pela IA — referência: `docs/specs/instalador-windows-e-atualizacao.md` e `docs/arquitetura/arquitetura.html`)*

---

## 1. Escopo Revisado

- **Identificador da mudança:** `instalador-windows-e-atualizacao` (OpenSpec / Ramo `feat/24-instalador-windows`)
- **Spec de referência:** `docs/specs/instalador-windows-e-atualizacao.md`
- **Arquivos tocados no diff:**
  - `.github/workflows/release.yml`
  - `README.md`
  - `pyproject.toml`
  - `src/tradutor/infra/updater.py`
  - `src/tradutor/tui/app.py`
  - `src/tradutor/tui/screens/config.py`
  - `src/tradutor/tui/screens/update.py`
  - `tests/infra/test_updater.py`
  - `tests/tui/test_updater_tui.py`
  - `installer/tradutor-setup.iss` *(novo)*
  - `scripts/build_installer.py` *(novo)*
  - `scripts/generate_icons.py` *(novo)*
  - `assets/logo.png` *(novo)*
  - `assets/app.ico` *(novo)*

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

- **[installer/tradutor-setup.iss:5]**: A definição `#define MyAppVersion "0.6.0"` serve como fallback caso o compilador `iscc` seja invocado diretamente sem o argumento `/DMyAppVersion=...`. Como `scripts/build_installer.py` e o workflow de release sempre injetam a versão dinâmica via linha de comando, o fallback está seguro, mas vale mantê-lo alinhado em futuros bumps manuais.
- **[README.md:48-54]**: Na seção "Instalação > Como Executável Standalone (Windows)", convém enriquecer as instruções para destacar tanto o Instalador Oficial (`tradutor-ebook-setup.exe` - recomendado) quanto a versão portátil avulsa (`tradutor.exe`), alinhando o guia do usuário às novas opções de distribuição (etapa a ser refinada na skill `documentacao`).

---

## 5. Checklist de Fitness Functions (da spec)
*(só se aplica se a fonte for `docs/specs/<slug>.md`, formato completo — copiar os itens da Seção 6 e marcar cada um com base no diff, sem redebater se o critério em si faz sentido, só checar se foi atendido)*

- [x] **FF-01 (Compilação do Instalador com Ícone e PT-BR):** Script `installer/tradutor-setup.iss` estruturado com suporte declarativo a `BrazilianPortuguese.isl`, ícone multi-resolução `assets/app.ico` e integração no `scripts/build_installer.py` / `hatch run installer`.
- [x] **FF-02 (Instalação e Desinstalação Limpa):** Configurado para `%LOCALAPPDATA%\Programs\tradutor-ebook` sem requisição de privilégios de administrador (`PrivilegesRequired=lowest`), gerando atalhos opcionais e com rotina Pascal Script `NeedsAddPath` / `CurUninstallStepChanged` para manipulação segura e remoção do `PATH`.
- [x] **FF-03 (Detecção de Modo):** Função `is_installed_mode()` implementada em `src/tradutor/infra/updater.py`, retornando `True` quando `unins000.exe` está presente no diretório do executável e `False` para executáveis avulsos ou ambiente de desenvolvimento.
- [x] **FF-04 (Isolamento de Camadas):** `src/tradutor/infra/updater.py` não importa `tradutor.tui` nem `textual`, preservando a arquitetura hexagonal validada por `hatch run arch-check` (2 contratos mantidos, 0 quebrados).
- [x] **FF-05 (Cobertura de Testes >= 95%):** Suíte completa de testes unitários e de integração (`tests/infra/test_updater.py` e `tests/tui/test_updater_tui.py`) passando com 100% de sucesso (685 testes) e cobertura global de **95%** (`updater.py` com 96% e `update.py` com 95%).
- [x] **FF-06 (CI/CD Automatizado):** Pipeline [`.github/workflows/release.yml`](file:///C:/Users/vasco/Documents/Software/tradutor-ebook/.github/workflows/release.yml) atualizado com etapa Windows que instala o Inno Setup (`choco install innosetup`), executa `hatch run installer` e anexa ambos os artefatos (`dist/tradutor.exe` e `dist/tradutor-ebook-setup.exe`) à Release do GitHub.
- [x] **FF-07 (Integridade do Download):** `download_update()` faz download atômico em arquivo temporário `.tmp`, valida tamanho mínimo (> 1024 bytes) e integridade do cabeçalho executável PE (`MZ`) antes de promover para o arquivo final.

---

## 6. Conformidade Arquitetural (do `arquitetura.html`, se existir)

- **Regras de Acoplamento respeitadas?** Sim. O módulo `tradutor.infra.updater` situa-se na camada de infraestrutura externa e comunica-se apenas com a biblioteca padrão (`os`, `sys`, `pathlib`, `subprocess`, `webbrowser`), `httpx` e `platformdirs`. A tela `UpdateModal` e `ConfigScreen` interagem com o `updater` por meio de Workers assíncronos do Textual sem acoplamento reverso.
- **ADRs relevantes:**
  - **ADR-001 (Arquitetura Hexagonal):** Respeitada integralmente. O núcleo de domínio permanece 100% desacoplado de detalhes de distribuição e atualização do Windows.
  - **ADR-003 (Interface TUI Reativa com Executável Standalone para Windows):** Reforçada e expandida pela nova sistemática de distribuição dual (instalador e portátil).
  - **ADR-007 (Harness de Engenharia e Sensores):** Respeitada com `mypy --strict` verde (103 arquivos), `ruff` limpo e `import-linter` validado.

---

## 7. Lembrete de Atualização Arquitetural
*(o code-review NÃO atualiza o `arquitetura.html` — só sinaliza se é hora de rodar o `architecture-report`)*

- Esta mudança introduz componente(s), regra(s) de acoplamento ou ADR novos que ainda não estão no `docs/arquitetura/arquitetura.html`? **Sim** (novo fluxo de empacotamento Inno Setup, identidade visual/assets e a proposta da ADR-008 correspondente).
- *Rode a skill `architecture-report` antes de começar a próxima funcionalidade, para evitar que o dashboard fique desatualizado.*

---

## 8. Veredito

**PODE FINALIZAR SEM RESSALVAS**
