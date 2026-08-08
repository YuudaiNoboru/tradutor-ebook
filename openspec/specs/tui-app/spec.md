# tui-app Specification

## Purpose

Interface de terminal (TUI) em português para configurar e executar traduções: fluxo guiado da primeira execução à configuração da chave, estimativa, progresso com ETA e relatório final.

## Requirements

### Requirement: Primeira execução guiada
Na ausência de chave configurada, o sistema SHALL exibir um fluxo de boas-vindas que guia o usuário para configurar a chave do provider (com teste de conexão) antes de oferecer a tradução.

#### Scenario: Primeira execução
- **WHEN** o aplicativo inicia sem chave configurada
- **THEN** a interface orienta a configuração da chave passo a passo, permitindo testar a conexão

### Requirement: Tela de configuração
O sistema SHALL oferecer tela de configuração em português com: seleção de provedor (traduzindo o termo "provider"), chave (sempre mascarada) com teste de conexão, seleção dinâmica de modelo, idioma de origem/destino, política de termos e paralelismo.
- O campo de modelo SHALL ser do tipo dropdown (`Select`) se houver modelos disponíveis ou configurados.
- Se o teste de conexão retornar que a rota de modelos não existe ou está vazia, o sistema SHALL exibir um campo de texto (`Input`) para digitação manual do modelo.
- O modelo SHALL ser obrigatório para salvar a configuração.
- O modelo e as opções disponíveis SHALL ser associados de forma isolada ao provedor selecionado na UI.
- O teste de conexão na tela de configuração SHALL usar o provedor e modelo atualmente exibidos no formulário (UI), e não a versão salva em disco.

#### Scenario: Alterar configurações
- **WHEN** o usuário abre a tela de configuração
- **THEN** ele vê os campos com rótulos em português (como "Provedor" em vez de "Provider"), pode alterar provedor, modelo (inicialmente exibindo o modelo configurado para aquele provedor), idiomas, política e paralelismo, e a chave aparece mascarada.

#### Scenario: Troca de provedor reseta ou carrega modelo
- **WHEN** o usuário altera o provedor selecionado
- **AND** esse provedor já possui um modelo salvo no arquivo de configuração
- **THEN** o campo de seleção exibe apenas o modelo salvo como opção ativa.
- **BUT WHEN** o novo provedor não possui modelo salvo
- **THEN** o campo de seleção é limpo e desabilitado, exibindo a mensagem "Realize o teste de conexao para listar modelos...".

#### Scenario: Teste de conexão atualiza modelos
- **WHEN** o usuário clica em "Testar conexão"
- **AND** o provedor retorna uma lista de modelos
- **THEN** o dropdown de modelo é atualizado para exibir apenas a lista dinâmica de modelos da API.
- **AND** se o modelo atual não constar na lista, o primeiro modelo retornado é sugerido automaticamente.

#### Scenario: Rota de modelos indisponível ativa campo manual
- **WHEN** o usuário testa a conexão
- **AND** a API retorna que a rota de modelos não está disponível (404/405/vazia)
- **THEN** o dropdown de modelo é ocultado e o campo de texto de modelo manual é exibido e focado para o usuário digitar livremente.

### Requirement: Seleção de livro por navegação
Para facilitar o uso, o sistema SHALL permitir que o usuário navegue pelo sistema de arquivos e selecione o EPUB usando um componente de árvore de diretórios (como o `DirectoryTree` do Textual), em vez de exigir a digitação manual do caminho. O sistema SHALL permitir subir níveis na estrutura de pastas para acessar caminhos fora do diretório inicial.

#### Scenario: Selecionar livro na árvore de diretórios
- **WHEN** o usuário abre a tela de seleção de livro
- **THEN** ele vê uma árvore de diretórios para navegar e selecionar arquivos .epub, e pode subir de nível (diretório pai).

### Requirement: Identidade visual (Branding)
O sistema SHALL exibir o nome oficial do aplicativo, `LiberLingua`, no cabeçalho global (`Header.title`) de todas as telas da TUI.

#### Scenario: Exibir nome do app no cabeçalho
- **WHEN** o aplicativo inicia em qualquer tela
- **THEN** o cabeçalho global (`Header.title`) exibe o nome `LiberLingua`

### Requirement: Atalhos e rodapé globais
O sistema SHALL disponibilizar no rodapé (`Footer`) os atalhos globais de teclado: `q` para sair da aplicação, `c` para acessar a tela de configuração e `h` para abrir a ajuda. O rodapé MUST exibir dinamicamente no canto inferior direito a versão atual do sistema em execução (ex: `v0.4.0`), sem codificação manual. A tela de seleção de livro SHALL conter apenas os botões de ação essenciais (`[ Abrir livro ]` e `[ Subir pasta ]`), omitindo botões redundantes para ações cobertas pelos atalhos do rodapé.

#### Scenario: Atalhos globais ativos no rodapé
- **WHEN** o aplicativo está rodando em qualquer tela
- **THEN** o rodapé (`Footer`) exibe as teclas `q`, `c` e `h` correspondentes
- **AND** apresenta a versão atual em execução de forma legível e dinâmica no canto inferior direito

### Requirement: Tela de ajuda
Ao acionar o atalho `h`, o sistema SHALL exibir uma tela modal explicativa de ajuda. A ajuda SHALL cobrir as orientações sobre BYOK (chaves de API), fluxo de tradução, cache e o funcionamento do glossário de termos.

#### Scenario: Abrir e fechar ajuda
- **WHEN** o usuário pressiona o atalho de ajuda `h` em qualquer tela
- **THEN** a tela modal explicativa é aberta exibindo o guia de uso
- **AND** ao clicar no botão de fechar, ele retorna para a tela anterior

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

### Requirement: Opções de atualização na tela de configurações
A tela de configuração da TUI MUST disponibilizar um campo interativo de seleção/marcação para ativar ou desativar a checagem automática de atualizações. Ela MUST também exibir um botão "Verificar atualizações" que realiza a consulta ao GitHub sob demanda no momento do clique, exibindo o resultado em um aviso amigável na tela.

#### Scenario: Verificar atualizações sob demanda com sucesso
- **WHEN** o usuário clica no botão "Verificar atualizações"
- **AND** a rede responde normalmente
- **THEN** a TUI apresenta se existe ou não uma nova versão disponível, de forma clara
