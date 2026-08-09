## MODIFIED Requirements

### Requirement: Adapter compatível com API OpenAI
O sistema SHALL incluir adapters de LLM organizados modularmente por provider, podendo reutilizar o protocolo compatível com OpenAI. O adapter DeepSeek SHALL continuar sendo o padrão atual, e novos providers LLM compatíveis SHALL poder ser adicionados sem alterar o núcleo do domínio. As requisições de chat SHALL incluir um teto explícito de tokens de saída (`max_tokens`), de modo que respostas grandes não sejam cortadas por limites implícitos do provedor.

#### Scenario: Configuração padrão DeepSeek
- **WHEN** o usuário seleciona a família LLM sem alterar o provider
- **THEN** as traduções são feitas via adapter DeepSeek com o modelo padrão

#### Scenario: Endpoint alternativo compatível
- **WHEN** o usuário configura um `base_url` e modelo alternativos (ex.: Ollama local ou OpenRouter)
- **THEN** as traduções são feitas contra esse endpoint sem alteração do núcleo

#### Scenario: Novo provider compatível
- **WHEN** um novo módulo LLM compatível é disponibilizado
- **THEN** ele pode ser descoberto e selecionado sem modificar a porta ou o motor de tradução

#### Scenario: Teto de saída explícito
- **WHEN** o adapter envia um lote para a API de chat
- **THEN** o corpo da requisição inclui `max_tokens` com o teto de saída declarado pelo provider, evitando truncamento de respostas grandes

#### Scenario: Teto de saída indisponível
- **WHEN** o provider não declara teto de saída
- **THEN** a requisição não inclui `max_tokens` e a API usa seu comportamento padrão

### Requirement: Retry com backoff
O sistema SHALL repetir chamadas que falham por erro transitório (429, 5xx, timeout) com backoff exponencial e jitter, e SHALL reportar falha definitiva após esgotar as tentativas. Cada retry SHALL ser registrado no log de execução, sem expor segredos, para permitir diagnóstico de lentidão e rate limiting.

#### Scenario: Erro transitório recuperável
- **WHEN** uma chamada falha com 429 ou 5xx
- **THEN** o sistema tenta novamente com espera crescente e conclui a tradução quando a API responde

#### Scenario: Falha definitiva
- **WHEN** as tentativas se esgotam
- **THEN** o bloco é marcado como pendente de retomada e a execução continua nos demais blocos sem interromper o livro inteiro

#### Scenario: Retry registrado no log
- **WHEN** uma chamada falha por erro transitório ou resposta inválida
- **THEN** o log registra o motivo, o número da tentativa e o tempo de backoff, sem conter a chave da API
