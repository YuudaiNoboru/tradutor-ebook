## MODIFIED Requirements

### Requirement: Passada de glossário
O sistema SHALL executar a passada de glossário somente quando o provider selecionado declarar suporte ao contexto de glossário. Para providers de tradução automática sem esse suporte, a passada SHALL ser omitida e nenhum arquivo ou apêndice de glossário SHALL ser produzido como parte da tradução.

#### Scenario: Glossário com LLM
- **WHEN** o usuário traduz com um provider LLM
- **THEN** o sistema gera ou carrega o glossário e o inclui nas traduções

#### Scenario: Provider comum sem glossário
- **WHEN** o usuário traduz com Google Web ou outro provider sem suporte
- **THEN** o sistema não executa a passada, não exige glossário e não adiciona apêndice de glossário

### Requirement: Passada de priming
O sistema SHALL executar a passada de priming somente quando o provider selecionado declarar suporte ao contexto de estilo. Para providers de tradução automática, a passada SHALL ser omitida.

#### Scenario: Priming com LLM
- **WHEN** um provider LLM suporta priming
- **THEN** o estilo e o tom extraídos são enviados no contexto dos lotes

#### Scenario: Priming indisponível
- **WHEN** o provider não suporta priming
- **THEN** a tradução começa sem chamada de priming e sem erro de configuração

### Requirement: Política de termos técnicos
O sistema SHALL aplicar a política configurável de termos somente para providers que suportarem contexto de termos. Para providers comuns, a opção SHALL ser desabilitada ou informada como não aplicável.

#### Scenario: Política com LLM
- **WHEN** a família LLM está selecionada
- **THEN** a política escolhida é aplicada no contexto da tradução

#### Scenario: Política não aplicável
- **WHEN** a família de tradução automática está selecionada
- **THEN** a UI não promete aplicação de política de termos e o motor não executa uma passada equivalente

### Requirement: Tradução em lotes
O sistema SHALL agrupar blocos conforme os limites declarados pelo provider, usando tokens para LLMs e caracteres/itens para providers de tradução automática, e SHALL respeitar a concorrência efetiva do provider selecionado.

#### Scenario: Lote limitado por caracteres
- **WHEN** um provider comum declara limite de caracteres menor que o lote atual
- **THEN** o motor divide os blocos antes da requisição sem cortar conteúdo protegido

### Requirement: Apêndice de glossário
O sistema SHALL adicionar apêndice de glossário somente quando uma passada de glossário foi executada e o provider selecionado oferece esse recurso.

#### Scenario: Apêndice com LLM
- **WHEN** a tradução LLM termina com glossário ativo
- **THEN** o EPUB contém o apêndice correspondente

#### Scenario: Tradução automática sem apêndice
- **WHEN** a tradução termina com provider comum
- **THEN** o EPUB não contém apêndice de glossário gerado pelo sistema
