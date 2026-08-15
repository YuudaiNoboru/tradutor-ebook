# windows-installer Specification

## Purpose

Provê um instalador executável oficial para Windows com assistente gráfico interativo (Wizard), suporte a instalação por usuário, atalhos no sistema, desinstalação limpa e comandos de build automatizados.

## Requirements

### Requirement: Assistente gráfico de instalação para Windows
O sistema MUST fornecer um pacote de instalação executável (`tradutor-ebook-setup.exe`) gerado via Inno Setup, com assistente gráfico moderno em Português do Brasil (`pt-BR`).

#### Scenario: Execução do assistente de instalação
- **WHEN** o usuário executa o arquivo `tradutor-ebook-setup.exe` no Windows
- **THEN** o instalador apresenta páginas intuitivas de Boas-vindas, Termos de Licença, Seleção de Pasta de Destino, Tarefas Adicionais e Conclusão com opção de executar o aplicativo

### Requirement: Instalação por usuário sem privilégios de administrador
O instalador MUST instalar o aplicativo no escopo do usuário atual (`PrivilegesRequired=lowest`) com diretório padrão sugerido em `%LOCALAPPDATA%\Programs\tradutor-ebook`.

#### Scenario: Instalação padrão sem prompt de UAC
- **WHEN** um usuário padrão do Windows executa o instalador
- **THEN** os arquivos são instalados no diretório `%LOCALAPPDATA%\Programs\tradutor-ebook` sem exibir solicitação de elevação de administrador (UAC)

### Requirement: Criação de atalhos e integração ao sistema
O instalador MUST permitir ao usuário optar pela criação de atalhos no Menu Iniciar e na Área de Trabalho com o ícone oficial do aplicativo, além de opção para registrar o executável na variável `PATH` do usuário.

#### Scenario: Seleção de atalhos no instalador
- **WHEN** o usuário seleciona as opções de atalho de Área de Trabalho e Menu Iniciar
- **THEN** o instalador cria os atalhos `.lnk` apontando para `tradutor.exe` associados ao ícone oficial do aplicativo

### Requirement: Desinstalação completa e limpa
O instalador MUST registrar uma entrada oficial no painel "Aplicativos Instalados" (ou Programas e Recursos) do Windows com desinstalador (`unins000.exe`).

#### Scenario: Desinstalação pelo painel do Windows
- **WHEN** o usuário solicita a desinstalação do aplicativo através do Windows
- **THEN** o desinstalador `unins000.exe` remove todos os arquivos instalados da pasta do aplicativo, atalhos do Menu Iniciar/Desktop e chaves de registro criadas pelo instalador

### Requirement: Automação de compilação do instalador
O repositório MUST conter o script de configuração Inno Setup (`installer/tradutor-setup.iss`), um utilitário local `scripts/build_installer.py` acessível via `hatch run installer` e integração no workflow de release do CI.

#### Scenario: Compilação do instalador via CI
- **WHEN** uma nova tag de versão `v*` é publicada no repositório
- **THEN** o workflow de release do GitHub Actions compila o binário `tradutor.exe`, empacota o instalador `tradutor-ebook-setup.exe` via Inno Setup e anexa ambos os arquivos à release
