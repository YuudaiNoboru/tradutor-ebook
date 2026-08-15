# auto-updater Specification

## Purpose

Permite que a aplicação verifique automaticamente a existência de novas versões lançadas no GitHub, realize o download seguro do instalador oficial em segundo plano no Modo Instalado ou redirecione para o navegador web no Modo Portátil.

## Requirements

### Requirement: Detecção de atualizações na inicialização
O sistema rodando como executável Windows compilado (frozen) MUST consultar a API de Releases do GitHub de forma assíncrona na inicialização se a opção de checagem automática estiver habilitada, identificando se a execução ocorre no Modo Instalado (presença de `unins000.exe`) ou no Modo Portátil.

#### Scenario: Versão atualizada
- **WHEN** o aplicativo inicializa e a versão retornada pelo GitHub é igual ou inferior à versão local `__version__`
- **THEN** nenhuma notificação ou prompt de atualização é exibido ao usuário

#### Scenario: Nova versão disponível
- **WHEN** o aplicativo inicializa e a versão retornada pelo GitHub é superior à versão local `__version__`
- **THEN** se estiver no Modo Instalado (desinstalador `unins000.exe` presente), a interface exibe modal com opção `[Baixar e Atualizar]` para o instalador oficial
- **AND** se estiver no Modo Portátil (sem `unins000.exe`), a interface exibe modal informando a nova versão com o botão `[Abrir no Navegador]`

### Requirement: Download atômico em segundo plano
O sistema MUST realizar o download do instalador oficial (`tradutor-ebook-setup.exe`) em segundo plano de forma assíncrona sem travar a interface da TUI, validando a integridade do arquivo temporário antes de habilitar o disparo da instalação.

#### Scenario: Download concluído com sucesso
- **WHEN** o usuário aceita baixar a nova versão no Modo Instalado
- **AND** o download do instalador oficial do GitHub é concluído e validado com sucesso
- **THEN** o sistema salva o executável do instalador no diretório temporário do sistema
- **AND** dispara a execução do instalador oficial com encerramento gracioso da aplicação

#### Scenario: Download falhou ou foi interrompido
- **WHEN** o download da atualização falha devido a erro de rede ou interrupção do aplicativo
- **THEN** o arquivo temporário incompleto é removido e a interface exibe uma mensagem de erro sem afetar a instalação atual

### Requirement: Execução transparente do instalador de atualização
O sistema MUST disparar o processo gráfico do instalador Inno Setup (`tradutor-ebook-setup.exe`) e encerrar o processo da aplicação imediatamente, delegando ao instalador nativo a substituição dos arquivos e atualização de atalhos.

#### Scenario: Disparo do instalador oficial
- **WHEN** o download do instalador de atualização é concluído com sucesso
- **THEN** o sistema invoca `subprocess.Popen([setup_path])` sem argumentos ocultos de PowerShell
- **AND** encerra a execução do aplicativo principal imediatamente via `os._exit(0)`

### Requirement: Redirecionamento da release no modo portátil
O sistema MUST permitir ao usuário do modo portátil abrir a página de releases do repositório no navegador web padrão ao clicar no botão correspondente.

#### Scenario: Abertura da release no navegador
- **WHEN** o usuário no modo portátil clica em `[Abrir no Navegador]` no modal de atualização
- **THEN** o sistema invoca o navegador padrão com a URL da release mais recente do GitHub e fecha o modal
