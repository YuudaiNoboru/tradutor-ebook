## MODIFIED Requirements

### Requirement: Porta Translator
O sistema SHALL expor uma porta de tradução para providers de LLM pela qual o núcleo solicita traduções sem conhecer o provider concreto. A chamada SHALL aceitar lote e contexto de LLM, incluindo idiomas, política, glossário e priming, e SHALL retornar traduções e uso de tokens. Essa porta SHALL ser distinta da porta de tradução automática tradicional.

#### Scenario: Tradução via porta de LLM
- **WHEN** o motor envia um lote a um provider LLM
- **THEN** recebe traduções alinhadas e uso de tokens sem referência ao adapter concreto

#### Scenario: Provider de outra família
- **WHEN** o usuário seleciona um provider de tradução automática
- **THEN** o motor não o instancia pela porta de LLM nem envia contexto de glossário ou priming

### Requirement: Adapter compatível com API OpenAI
O sistema SHALL incluir adapters de LLM organizados modularmente por provider, podendo reutilizar o protocolo compatível com OpenAI. O adapter DeepSeek SHALL continuar sendo o padrão atual, e novos providers LLM compatíveis SHALL poder ser adicionados sem alterar o núcleo do domínio.

#### Scenario: Configuração padrão DeepSeek
- **WHEN** o usuário seleciona a família LLM sem alterar o provider
- **THEN** as traduções são feitas via adapter DeepSeek com o modelo padrão

#### Scenario: Novo provider compatível
- **WHEN** um novo módulo LLM compatível é disponibilizado
- **THEN** ele pode ser descoberto e selecionado sem modificar a porta ou o motor de tradução
