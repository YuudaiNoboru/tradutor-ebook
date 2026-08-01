## Purpose

Interface de terminal (TUI) em português para configurar e executar traduções: fluxo guiado da primeira execução à configuração da chave, estimativa, progresso com ETA e relatório final.

## ADDED Requirements

### Requirement: Primeira execução guiada
Na ausência de chave configurada, o sistema SHALL exibir um fluxo de boas-vindas que guia o usuário para configurar a chave do provider (com teste de conexão) antes de oferecer a tradução.

#### Scenario: Primeira execução
- **WHEN** o aplicativo inicia sem chave configurada
- **THEN** a interface orienta a configuração da chave passo a passo, permitindo testar a conexão

### Requirement: Tela de configuração
O sistema SHALL oferecer tela de configuração com: seleção de provider, chave (sempre mascarada) com teste de conexão, idioma de origem/destino, política de termos e paralelismo.

#### Scenario: Alterar configurações
- **WHEN** o usuário abre a tela de configuração
- **THEN** pode alterar provider, idiomas, política e paralelismo, e a chave aparece mascarada

### Requirement: Tela de estimativa com confirmação
Antes de iniciar, o sistema SHALL exibir a tela de estimativa (resumo do livro, tokens, custo em US$, tempo) com o aviso de estimativa e a recomendação de limites, e SHALL exigir confirmação para começar.

#### Scenario: Confirmar ou ajustar
- **WHEN** a tela de estimativa é exibida
- **THEN** o usuário pode confirmar a tradução, ajustar o paralelismo ou cancelar

### Requirement: Progresso com ETA e cancelamento seguro
Durante a tradução, o sistema SHALL exibir progresso por bloco/capítulo e ETA recalculado a partir da vazão medida; o cancelamento SHALL preservar o progresso no cache para retomada.

#### Scenario: Tradução em andamento
- **WHEN** a tradução está em andamento
- **THEN** a interface mostra progresso, ETA e eventos de log redigidos

#### Scenario: Cancelamento no meio
- **WHEN** o usuário cancela a tradução
- **THEN** o sistema encerra de forma ordenada e o progresso fica disponível para retomada

### Requirement: Relatório final
Ao terminar, o sistema SHALL exibir o relatório real-vs-previsto (custo US$, tokens) e o caminho do arquivo de saída.

#### Scenario: Tradução concluída
- **WHEN** a tradução termina
- **THEN** a interface mostra o relatório de custo e o caminho do EPUB gerado

### Requirement: Retomada com cache detectado
Quando existe tradução em cache para o livro e configuração atuais, o sistema SHALL informar e oferecer continuar a partir do progresso existente.

#### Scenario: Livro já parcialmente traduzido
- **WHEN** o usuário seleciona um livro com cache existente compatível
- **THEN** a interface informa o progresso armazenado e oferece continuar ou recomeçar

### Requirement: Mensagens de erro claras
O sistema SHALL apresentar erros em português com orientação acionável: livro protegido por DRM, chave ausente ou inválida, configuração inválida, falha de rede, teto de gasto atingido.

#### Scenario: Erro acionável
- **WHEN** ocorre um erro evitável (ex.: livro protegido)
- **THEN** a mensagem explica o problema e o que fazer, sem expor segredos
