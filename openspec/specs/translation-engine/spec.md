# translation-engine Specification

## Purpose

Orquestra a tradução com qualidade profissional: passada de glossário, passada de priming, tradução em lotes com paralelismo e apêndice de glossário — produzindo texto natural, consistente e sem traduzir código.

## Requirements

### Requirement: Passada de glossário
O sistema SHALL executar a passada de glossário somente quando o provider selecionado declarar suporte ao contexto de glossário. Para providers de tradução automática sem esse suporte, a passada SHALL ser omitida e nenhum arquivo ou apêndice de glossário SHALL ser produzido como parte da tradução.

#### Scenario: Glossário gerado e aplicado
- **WHEN** o usuário traduz um livro de computação
- **THEN** o sistema gera um glossário com os termos técnicos e o usa no contexto, de modo que o mesmo termo seja traduzido consistentemente ao longo do livro

#### Scenario: Glossário editado manualmente
- **WHEN** o usuário edita o arquivo JSON do glossário antes de traduzir
- **THEN** a tradução respeita as entradas editadas

#### Scenario: Glossário com LLM
- **WHEN** o usuário traduz com um provider LLM
- **THEN** o sistema gera ou carrega o glossário e o inclui nas traduções

#### Scenario: Provider comum sem glossário
- **WHEN** o usuário traduz com Google Web ou outro provider sem suporte
- **THEN** o sistema não executa a passada, não exige glossário e não adiciona apêndice de glossário

### Requirement: Passada de priming
O sistema SHALL executar a passada de priming somente quando o provider selecionado declarar suporte ao contexto de estilo. Para providers de tradução automática, a passada SHALL ser omitida.

#### Scenario: Tom consistente
- **WHEN** um livro possui estilo informal ou formal característico
- **THEN** a tradução mantém esse estilo ao longo de todo o livro

#### Scenario: Priming com LLM
- **WHEN** um provider LLM suporta priming
- **THEN** o estilo e o tom extraídos são enviados no contexto dos lotes

#### Scenario: Priming indisponível
- **WHEN** o provider não suporta priming
- **THEN** a tradução começa sem chamada de priming e sem erro de configuração

### Requirement: Política de termos técnicos
O sistema SHALL aplicar a política configurável de termos somente para providers que suportarem contexto de termos. Para providers comuns, a opção SHALL ser desabilitada ou informada como não aplicável.

#### Scenario: Política híbrida aplicada
- **WHEN** a política é híbrida e um termo técnico ocorre no livro
- **THEN** o termo aparece traduzido com o original preservado conforme a política, em todo o livro

#### Scenario: Política com LLM
- **WHEN** a família LLM está selecionada
- **THEN** a política escolhida é aplicada no contexto da tradução

#### Scenario: Política não aplicável
- **WHEN** a família de tradução automática está selecionada
- **THEN** a UI não promete aplicação de política de termos e o motor não executa uma passada equivalente

### Requirement: Tradução em lotes
O sistema SHALL agrupar blocos conforme os limites declarados pelo provider, usando tokens para LLMs e caracteres/itens para providers de tradução automática, e SHALL respeitar a concorrência efetiva do provider selecionado.

#### Scenario: Livro longo
- **WHEN** um livro possui muitos capítulos
- **THEN** a tradução acontece em lotes paralelos, com progresso mensurável por bloco

#### Scenario: Lote limitado por caracteres
- **WHEN** um provider comum declara limite de caracteres menor que o lote atual
- **THEN** o motor divide os blocos antes da requisição sem cortar conteúdo protegido

### Requirement: Preservação de placeholders na saída
O sistema SHALL verificar, após cada lote, que todos os placeholders de conteúdo protegido retornaram intactos; divergências SHALL ser tratadas como falha do bloco (retry).

#### Scenario: Placeholder corrompido
- **WHEN** uma resposta não reproduz fielmente um placeholder de código
- **THEN** o bloco é reprocessado, e o código nunca é alterado na saída

### Requirement: Apêndice de glossário
O sistema SHALL adicionar apêndice de glossário somente quando uma passada de glossário foi executada e o provider selecionado oferece esse recurso.

#### Scenario: Livro com apêndice
- **WHEN** a tradução termina
- **THEN** o EPUB de saída contém um apêndice de termos técnicos com as entradas original → tradução

#### Scenario: Apêndice com LLM
- **WHEN** a tradução LLM termina com glossário ativo
- **THEN** o EPUB contém o apêndice correspondente

#### Scenario: Tradução automática sem apêndice
- **WHEN** a tradução termina com provider comum
- **THEN** o EPUB não contém apêndice de glossário gerado pelo sistema

### Requirement: Idiomas de origem e destino
O sistema SHALL aceitar idioma de origem configurável com default de detecção automática, e idioma de destino configurável com default `pt-BR`.

#### Scenario: Destino padrão
- **WHEN** o usuário não altera os idiomas
- **THEN** a tradução é feita de origem detectada para pt-BR

### Requirement: Saída apenas traduzida
O texto de saída SHALL ser natural, sem marcas de IA, colchetes, notas ou rótulos de tradução no corpo do livro.

#### Scenario: Corpo limpo
- **WHEN** o usuário abre o livro traduzido
- **THEN** o texto flui como um livro publicado, sem anotações de origem automatizada
