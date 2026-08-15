# Especificação da Funcionalidade: Sistemática de Instalação e Atualização Windows

---

## 1. Entrada do Desenvolvedor: Mapeamento de Atores & Ações
*(consolidado com base nos requisitos da Issue #24 e direcionamentos do desenvolvedor)*

### Contexto / Objetivo Resumido
Disponibilizar uma experiência nativa de instalação no Windows através de um assistente gráfico (*Wizard* clássico "Avançar, Avançar, Concluir"), com suporte a instalação, atualização e desinstalação limpa, geração de atalhos e seleção de diretório, além de fornecer uma versão portátil avulsa e reformular a sistemática de atualização de forma segura (sem scripts ocultos em PowerShell) para eliminar falsos-positivos e travamentos no Windows Defender.

### Papéis de Usuário Envolvidos
- **Leitor no Windows (Modo Instalador):** Usuário que prefere instalar o aplicativo com atalhos no Menu Iniciar/Desktop e gerenciamento pelo Windows.
- **Leitor no Windows (Modo Portátil):** Usuário que executa o binário único `tradutor.exe` diretamente sem instalar.
- **Desenvolvedor (Mantenedor):** Responsável por gerar os pacotes e manter os fluxos de CI/CD automatizados.
- **Sistema (Background):** Gerenciador de detecção de versão, download do instalador e disparo do assistente.

---

### Ator: Leitor no Windows (Modo Instalador)
- **US-01:** Como leitor no Windows, quero baixar e executar um instalador padrão (`tradutor-ebook-setup.exe`) com um assistente visual para instalar o aplicativo na minha conta sem precisar de privilégios de administrador (UAC).
- **US-02:** Como leitor no Windows, quero poder escolher o diretório de instalação (com sugestão padrão em `%LOCALAPPDATA%\Programs\tradutor-ebook`) e optar por criar atalhos na Área de Trabalho e no Menu Iniciar, além de opcionalmente adicionar o comando `tradutor` ao `PATH`.
- **US-03:** Como leitor no Windows, quando houver uma nova versão, quero ser avisado na TUI, baixar o assistente de instalação e acompanhar as etapas visuais do instalador para ter transparência e confiança no processo de atualização.
- **US-04:** Como leitor no Windows, quero poder desinstalar o aplicativo de forma limpa pelo painel "Aplicativos Instalados" do Windows, removendo binários e atalhos.

### Ator: Leitor no Windows (Modo Portátil)
- **US-05:** Como leitor no Windows, quero poder baixar e rodar o executável único portátil `tradutor.exe` sem necessidade de instalação.
- **US-06:** Como leitor no Windows (Modo Portátil), quando houver nova versão, quero ser avisado na TUI e ter um link direto para abrir a página de download da release no navegador, sem rotinas de auto-atualização silenciosa que possam bloquear o executável.

### Ator: Desenvolvedor (Mantenedor)
- **DEV-01:** Como desenvolvedor, quero que o fluxo de CI ([`.github/workflows/release.yml`](file:///C:/Users/vasco/Documents/Software/tradutor-ebook/.github/workflows/release.yml)) gere e anexe automaticamente à GitHub Release tanto a versão portátil (`tradutor.exe`) quanto o instalador oficial (`tradutor-ebook-setup.exe`).
- **DEV-02:** Como desenvolvedor, quero um script/comando local no [`pyproject.toml`](file:///C:/Users/vasco/Documents/Software/tradutor-ebook/pyproject.toml) para testar a compilação do instalador via Inno Setup localmente de forma simples.

### Ator: Sistema (Automações / Background)
- **SYS-01:** O sistema deve identificar dinamicamente se está executando no Modo Instalado (presença de `unins000.exe` no diretório do executável) ou no Modo Portátil.
- **SYS-02:** No Modo Instalado, ao disparar a atualização, o sistema deve baixar o instalador oficial para pasta temporária e executá-lo em modo visual com encerramento gracioso do processo atual, delegando ao Inno Setup a substituição atômica dos binários.
- **SYS-03:** O sistema deve eliminar totalmente o script auxiliar `update_helper.ps1` e execuções ocultas de PowerShell com bypass de política de segurança, garantindo conformidade com o Windows Defender/SmartScreen.

---

## 2. Análise Arquitetônica & Trade-offs

### Características Arquitetônicas Críticas (-ilities)
- **Usabilidade & Portabilidade (Guia #5):** Fornece aos usuários de Windows a experiência padrão esperada da plataforma (Wizard gráfico com páginas claras de Boas-vindas, Diretório, Atalhos, Licença e Conclusão), mantendo a opção do binário portátil standalone.
- **Segurança & Integridade:** Elimina disparos de heurísticas de antivírus causados por scripts PowerShell em segundo plano (`-WindowStyle Hidden -ExecutionPolicy Bypass`), utilizando o subsistema nativo do Inno Setup para substituição de arquivos.
- **Manutenibilidade & Testabilidade:** Separação limpa entre a camada de infraestrutura ([`src/tradutor/infra/updater.py`](file:///C:/Users/vasco/Documents/Software/tradutor-ebook/src/tradutor/infra/updater.py)) e as telas da TUI ([`src/tradutor/tui/screens/update.py`](file:///C:/Users/vasco/Documents/Software/tradutor-ebook/src/tradutor/tui/screens/update.py)), permitindo testes unitários com mocks de chamadas de SO e HTTP.

### Trade-offs Aceitos
> **Decisão de Trade-off:** 
> - **Instalação Per-User sem UAC (`PrivilegesRequired=lowest`):** Optou-se por instalar por padrão em `%LOCALAPPDATA%\Programs\tradutor-ebook` em vez de `C:\Program Files\`. Isso evita solicitar elevação de privilégios de administrador para usuários comuns e garante permissão de escrita nativa no diretório da aplicação, simplificando o processo de instalação e atualização.
> - **Atualização Visual com Wizard vs Silenciosa em Background:** Sacrifica-se a atualização 100% invisível em prol de máxima transparência e confiabilidade percebida pelo usuário (que acompanha o progresso no Wizard oficial).
> - **Modo Portátil sem In-Place Update:** Não realiza substituição forçada em memória do binário avulso portátil; em vez disso, redireciona o usuário para a página de releases do navegador, prevenindo falhas de *file lock* e bloqueios de segurança do sistema operacional.

---

## 3. Estrutura Física & Módulos

### Mapeamento no Projeto Existente
```text
tradutor-ebook/
├── .github/
│   └── workflows/
│       └── release.yml                 <-- [MODIFICADO] Adiciona step de compilação Inno Setup e anexo do instalador
├── assets/                              <-- [NOVO DIRETÓRIO]
│   ├── logo.png                        <-- [NOVO] Logo oficial em alta resolução
│   └── app.ico                         <-- [NOVO] Ícone Windows multi-resolução (16x16 a 256x256)
├── installer/                           <-- [NOVO DIRETÓRIO]
│   └── tradutor-setup.iss              <-- [NOVO] Script declarativo Inno Setup (pt-BR, ícone, atalhos, PATH)
├── scripts/
│   ├── build_installer.py             <-- [NOVO] Script auxiliar para compilação local do instalador via iscc
│   └── generate_icons.py              <-- [NOVO] Utilitário para conversão da imagem base para .ico multi-resolução
├── src/
│   └── tradutor/
│       ├── infra/
│       │   └── updater.py              <-- [MODIFICADO] Remove script PS1; adiciona detecção de modo, validação SHA256 e disparo de setup
│       └── tui/
│           └── screens/
│               └── update.py           <-- [MODIFICADO] Adapta modal para modo instalado vs modo portátil (browser)
├── pyproject.toml                      <-- [MODIFICADO] Adiciona comando hatch para build do instalador
└── tests/
    └── test_updater.py                 <-- [MODIFICADO] Cobertura dos novos fluxos de detecção, download, SHA256 e disparo
```

### Regras de Acoplamento & Limites
- **`tradutor.infra.updater`:**
  - **Pode Importar:** `pathlib`, `os`, `sys`, `subprocess`, `webbrowser`, `httpx`, `hashlib`, `platformdirs`.
  - **NÃO Pode Importar:** `tradutor.tui`, `textual`.
- **`tradutor.tui.screens.update`:**
  - **Pode Importar:** `tradutor.infra.updater` para invocar checagens e disparos.
  - **Padrão de Comunicação:** Injeção de dependência / Workers assíncronos do Textual (`@work(thread=True)`).

---

## 4. Fluxo de Execução & Casos de Borda

### Sequência Lógica — Modo Instalado (Atualização)
1. **[Disparo]:** A TUI (na inicialização ou via menu de configurações) executa a checagem em segundo plano via `check_for_update(__version__)`.
2. **[Detecção]:** O `updater` consulta o GitHub API e localiza o asset `tradutor-ebook-setup.exe`.
3. **[Notificação]:** A TUI exibe o `UpdateModal` informando a versão disponível com o botão `[Baixar e Atualizar]`.
4. **[Download & Validação]:** Ao clicar, um Worker faz o download atômico do instalador para `%TEMP%\tradutor-ebook-setup-vX.Y.Z.exe` e valida a integridade do arquivo baixado (tamanho e SHA-256 quando disponível).
5. **[Transição]:** O `updater` invoca `launch_installer_and_exit()`, que dispara o processo do instalador gráfico (`subprocess.Popen([setup_path])`) e encerra o aplicativo Python imediatamente via `os._exit(0)`.
6. **[Instalação]:** O usuário visualiza o assistente do Inno Setup em Português do Brasil com ícone oficial, avança pelas etapas e conclui a instalação, com opção de reiniciar o aplicativo atualizado.

### Sequência Lógica — Modo Portátil
1. **[Disparo & Detecção]:** O `updater` detecta que não há `unins000.exe` no diretório do executável (`is_installed_mode() == False`).
2. **[Notificação]:** A TUI exibe o `UpdateModal` com mensagem orientativa: *"Nova versão disponível! No modo portátil, baixe a nova versão pelo navegador."* e botões `[Abrir no Navegador]` e `[Fechar]`.
3. **[Ação]:** O botão abre diretamente a URL da release no navegador padrão (`webbrowser.open(release_url)`).

### Casos de Borda e Erros
- **Inno Setup Não Instalado no Ambiente Local de Dev:** O script `scripts/build_installer.py` verifica a presença de `ISCC.exe` no `PATH` ou em `C:\Program Files (x86)\Inno Setup 6\ISCC.exe` e emite mensagem clara de orientação caso não esteja instalado.
- **Conexão Interrompida / Arquivo Incompleto durante Download:** O download é feito em arquivo temporário `.tmp` e só é promovido após validação. Em caso de erro de rede ou timeout, o `.tmp` é removido e o modal exibe o estado de erro amigável sem corromper arquivos existentes.
- **Múltiplas Instâncias em Execução durante Atualização:** A diretiva `CloseApplications=yes` do Inno Setup solicita ao usuário o fechamento de instâncias residuais caso ainda estejam abertas.
- **PATH Duplicado no Windows:** A rotina do Inno Setup no Registro do Windows verifica se o caminho já existe na variável de ambiente de usuário antes de anexar.

---

## 5. Proposta de ADR — Registro de Decisão Arquitetônica

- **Título:** ADR-006: Sistemática de Instalação Inno Setup, Identidade Visual e Atualização Transparente no Windows
- **Contexto:** Usuários de Windows necessitam de um fluxo de instalação convencional (atalhos, desinstalador, seleção de pasta, idioma PT-BR, ícone nativo), e a rotina anterior de auto-atualização in-place via scripts PowerShell ocultos gerava falsos-positivos e bloqueios no Windows Defender.
- **Decisão:** Adotar o Inno Setup (`iscc`) com suporte nativo a PT-BR (`BrazilianPortuguese.isl`), ícone multi-resolução (`app.ico`) e instalação per-user (`PrivilegesRequired=lowest`); publicar artefato duplo na release (`tradutor.exe` e `tradutor-ebook-setup.exe`); e reestruturar a atualização para delegar ao instalador gráfico oficial a sobreposição de arquivos no modo instalado com validação de integridade, desativando auto-atualização in-place no modo portátil em favor de abertura da release no navegador.
- **Consequências:**
  - *Positivas:* Experiência de instalação nativa de alta qualidade em português com identidade visual profissional; eliminação total de disparos de antivírus; desinstalação limpa no Painel de Controle; zero scripts ocultos de PowerShell.
  - *Negativas:* Usuários do modo portátil precisam baixar o novo `.exe` manualmente pelo navegador quando houver release nova.

---

## 6. Funções de Aptidão (Fitness Functions) & Critérios de Aceite

- [ ] **FF-01 (Compilação do Instalador com Ícone e PT-BR):** O script `installer/tradutor-setup.iss` compila com sucesso via `iscc` gerando `tradutor-ebook-setup.exe` com o idioma em Português do Brasil e ícone embutido.
- [ ] **FF-02 (Instalação e Desinstalação Limpa):** O instalador instala o aplicativo em `%LOCALAPPDATA%\Programs\tradutor-ebook`, cria atalhos funcionais com ícone e o desinstalador `unins000.exe` remove todos os arquivos da pasta e atalhos.
- [ ] **FF-03 (Detecção de Modo):** A função `is_installed_mode()` retorna `True` quando `unins000.exe` está presente e `False` para executáveis avulsos.
- [ ] **FF-04 (Isolamento de Camadas):** O módulo `updater.py` não importa Textual nem componentes de UI (validado via `hatch run arch-check`).
- [ ] **FF-05 (Cobertura de Testes >= 95%):** Toda a nova lógica em `src/tradutor/infra/updater.py` e `src/tradutor/tui/screens/update.py` é coberta por testes com `hatch run cov` mantendo o gate global >= 95%.
- [ ] **FF-06 (CI/CD Automatizado):** O workflow [`.github/workflows/release.yml`](file:///C:/Users/vasco/Documents/Software/tradutor-ebook/.github/workflows/release.yml) compila e anexa ambos os arquivos (`tradutor.exe` e `tradutor-ebook-setup.exe`) na release do GitHub.
- [ ] **FF-07 (Integridade do Download):** O fluxo de download do setup valida o arquivo recebido antes de chamar a execução do processo do instalador.
