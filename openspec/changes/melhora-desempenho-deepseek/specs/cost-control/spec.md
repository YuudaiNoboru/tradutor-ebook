## MODIFIED Requirements

### Requirement: Estimativa pré-voo
O sistema SHALL apresentar, antes da tradução, uma estimativa adequada ao provider selecionado. Para LLMs, SHALL exibir tokens, custo em US$ e tempo; para providers sem medição de tokens ou cobrança por credencial do usuário, SHALL exibir caracteres/blocos, custo como não mensurável ou não aplicável e tempo estimado. O tempo estimado SHALL usar a latência por lote declarada pelo provider quando disponível; sem declaração, SHALL usar o valor padrão genérico.

#### Scenario: Estimativa exibida antes de traduzir
- **WHEN** o usuário seleciona um livro e confirma as configurações
- **THEN** a tela mostra tokens e custo estimados em US$ e o tempo estimado, e a tradução só começa após confirmação

#### Scenario: Código não entra na conta
- **WHEN** um livro possui muitos blocos de código
- **THEN** a estimativa considera apenas o texto que será efetivamente enviado ao modelo

#### Scenario: Estimativa LLM
- **WHEN** o usuário seleciona um provider LLM com preços configurados
- **THEN** a tela exibe tokens e custo estimados em US$

#### Scenario: Estimativa Google Web
- **WHEN** o usuário seleciona Google Web
- **THEN** a tela não apresenta zero tokens como se nenhum conteúdo fosse processado e informa que o serviço não fornece medição de uso

#### Scenario: Latência declarada pelo provider
- **WHEN** o provider selecionado declara uma latência média por lote (ex.: DeepSeek ~90s)
- **THEN** o tempo estimado usa essa latência, resultando em uma estimativa alinhada com a geração real de respostas longas
