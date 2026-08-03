# llm-provider Specification

## Purpose

Expõe uma porta única de tradução para qualquer provedor de LLM, implementada hoje por um adapter compatível com a API da OpenAI (DeepSeek) com `base_url` e modelo configuráveis.

## Requirements

### Requirement: Porta Translator
O sistema SHALL expor uma porta de tradução pela qual o núcleo do domínio solicita traduções sem conhecer o provedor concreto. A chamada SHALL aceitar um lote de blocos e contexto (idiomas, política, glossário, priming) e SHALL retornar as traduções e o uso de tokens.

#### Scenario: Tradução via porta
- **WHEN** o motor de tradução envia um lote pela porta
- **THEN** recebe as traduções dos blocos e os tokens de entrada/saída consumidos, sem referência ao provedor concreto

### Requirement: Adapter compatível com API OpenAI
O sistema SHALL incluir um adapter que fala o protocolo de chat completions compatível com OpenAI, com `base_url` e modelo configuráveis. O padrão SHALL apontar para a DeepSeek.

#### Scenario: Configuração padrão DeepSeek
- **WHEN** o usuário usa a configuração padrão
- **THEN** as traduções são feitas via API da DeepSeek com o modelo padrão

#### Scenario: Endpoint alternativo compatível
- **WHEN** o usuário configura um `base_url` e modelo alternativos (ex.: Ollama local ou OpenRouter)
- **THEN** as traduções são feitas contra esse endpoint sem alteração do núcleo

### Requirement: Retry com backoff
O sistema SHALL repetir chamadas que falham por erro transitório (429, 5xx, timeout) com backoff exponencial e jitter, e SHALL reportar falha definitiva após esgotar as tentativas.

#### Scenario: Erro transitório recuperável
- **WHEN** uma chamada falha com 429 ou 5xx
- **THEN** o sistema tenta novamente com espera crescente e conclui a tradução quando a API responde

#### Scenario: Falha definitiva
- **WHEN** as tentativas se esgotam
- **THEN** o bloco é marcado como pendente de retomada e a execução continua nos demais blocos sem interromper o livro inteiro

### Requirement: Exposição do uso de tokens
O sistema SHALL expor os tokens reais de entrada e saída de cada resposta, para fins de relatório de custo.

#### Scenario: Uso reportado
- **WHEN** uma tradução é concluída
- **THEN** o uso de tokens (entrada/saída) fica disponível para o relatório de custo

### Requirement: Teste de conexão
O sistema SHALL permitir verificar a conexão com o provedor (chave, base_url e modelo) antes de iniciar uma tradução, com mensagens claras de sucesso ou erro.
- O teste de conexão SHALL retornar a lista de modelos disponíveis quando a rota do provedor for suportada.
- Se a rota de modelos retornar status 404, 405 ou 501, a conexão SHALL ser considerada válida (caso a chave e rede estejam corretas), retornando uma lista vazia de modelos e indicando que a rota é indisponível.

#### Scenario: Conexão válida com rota de modelos
- **WHEN** o usuário testa a conexão com credenciais válidas e a rota `/models` funciona
- **THEN** o sistema confirma a conexão e retorna a lista completa de modelos disponíveis

#### Scenario: Conexão válida com rota de modelos indisponível
- **WHEN** o usuário testa a conexão com credenciais válidas e a rota `/models` retorna status 404 ou 405
- **THEN** o sistema confirma a conexão como OK mas indica que a rota de modelos está indisponível, retornando uma lista de modelos vazia

#### Scenario: Conexão inválida
- **WHEN** o usuário testa a conexão com chave inválida
- **THEN** a interface mostra erro claro indicando problema de autenticação

### Requirement: Chave fora do núcleo
O adapter SHALL obter a chave da API por meio da porta de segredos — o núcleo do domínio nunca SHALL receber ou armazenar chaves.

#### Scenario: Domínio sem contato com chave
- **WHEN** o pipeline de tradução executa
- **THEN** nenhuma chave atravessa o código do núcleo do domínio
