## MODIFIED Requirements

### Requirement: Tela de configuração
O sistema SHALL oferecer tela de configuração em português com: seleção de provedor, chave mascarada com teste de conexão, seleção dinâmica de modelo, idioma de origem/destino, política de termos e paralelismo.
- O limite máximo permitido no campo de paralelismo SHALL ser calculado dinamicamente como `min(20, provider_max_concurrency)` e exibido como dica explicativa na tela.
- O campo de paralelismo MUST validar e impedir valores superiores a esse limite dinâmico.

#### Scenario: Alterar configurações
- **WHEN** o usuário abre a tela de configuração
- **THEN** ele vê os campos com rótulos em português, dica visual do limite de paralelismo dinâmico (ex: máximo 20 para DeepSeek) e validação ativada.

#### Scenario: Troca de provedor reseta ou carrega modelo
- **WHEN** o usuário altera o provedor selecionado
- **AND** esse provedor já possui um modelo salvo no arquivo de configuração
- **THEN** o campo de seleção exibe apenas o modelo salvo como opção ativa e atualiza a dica de limite de paralelismo.
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

### Requirement: Tela de estimativa com confirmação
Antes de iniciar, o sistema SHALL exibir a tela de estimativa e configuração do e-book (resumo do livro, tokens, custo em US$, tempo), contendo a opção selecionável `[X] Gerar Glossário e Guia de Estilo` (exibida apenas para provedores da família LLM), exigindo confirmação para iniciar a tradução.

#### Scenario: Confirmar ou ajustar
- **WHEN** a tela de estimativa e configuração do e-book é exibida para um provider LLM
- **THEN** o usuário visualiza o checkbox "Gerar Glossário e Guia de Estilo", ajusta o paralelismo dentro do limite e confirma a tradução.
