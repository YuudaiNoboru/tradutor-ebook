# auto-updater Specification

## Purpose

Permite que a aplicação verifique automaticamente a existência de novas versões lançadas no GitHub, realize o download seguro em segundo plano e proceda com a auto-substituição atômica e reinicialização do executável no Windows.

## Requirements

### Requirement: Detecção de atualizações na inicialização
O sistema rodando como executável Windows compilado (frozen) MUST consultar a API de Releases do GitHub de forma assíncrona na inicialização se a opção de checagem automática estiver habilitada.

#### Scenario: Versão atualizada
- **WHEN** o aplicativo inicializa e a versão retornada pelo GitHub é igual ou inferior à versão local `__version__`
- **THEN** nenhuma notificação ou prompt de atualização é exibido ao usuário

#### Scenario: Nova versão disponível
- **WHEN** o aplicativo inicializa e a versão retornada pelo GitHub é superior à versão local `__version__`
- **AND** não há atualização pendente já gravada em cache
- **THEN** a interface exibe um modal amigável convidando o usuário a baixar a nova versão

### Requirement: Download atômico em segundo plano
O sistema MUST realizar o download do novo binário `.exe` em segundo plano de forma assíncrona sem travar a interface da TUI. O arquivo baixado MUST ser gravado temporariamente e só deve ser marcado como atualização pendente válida após a conclusão bem-sucedida do download.

#### Scenario: Download concluído com sucesso
- **WHEN** o usuário aceita baixar a nova versão
- **AND** o download do binário do GitHub é concluído com sucesso
- **THEN** o sistema salva o executável como `pending_update.exe` e cria o manifesto `pending_update.json` no diretório de cache
- **AND** a interface pergunta se o usuário deseja reiniciar para aplicar imediatamente

#### Scenario: Download falhou ou foi interrompido
- **WHEN** o download da atualização falha devido a erro de rede ou interrupção do aplicativo
- **THEN** o arquivo incompleto é ignorado e nenhum estado de atualização pendente é gerado ou gravado no cache

### Requirement: Execução do Delayed Update
O sistema MUST checar e aplicar atualizações pendentes previamente baixadas na inicialização de forma automática.

#### Scenario: Atualização pendente detectada no boot
- **WHEN** o aplicativo é iniciado
- **AND** o arquivo `pending_update.exe` e seu manifesto `pending_update.json` correspondente existem no diretório de cache
- **AND** a versão indicada no manifesto é superior à versão atual do aplicativo
- **THEN** o sistema avisa o usuário que a atualização já foi baixada anteriormente e será aplicada imediatamente
- **AND** encerra o aplicativo executando o processo de auto-substituição

### Requirement: Auto-substituição física do binário
O sistema MUST gerar e lançar de forma assíncrona um script batch temporário `.bat` encarregado de aguardar a saída física do PID do aplicativo original antes de sobrescrevê-lo com a versão pendente, relançá-lo e apagar o próprio script.

#### Scenario: Execução do script batch de atualização
- **WHEN** a atualização é disparada imediatamente
- **THEN** o sistema cria e executa o script `update_helper.bat` que monitora o processo pai
- **AND** finaliza o aplicativo principal chamando o encerramento do processo (`sys.exit()`)
