# translation-engine Specification

## Purpose

Orquestra a tradução com qualidade profissional: passada de glossário, passada de priming, tradução em lotes com paralelismo e apêndice de glossário — produzindo texto natural, consistente e sem traduzir código.

## Requirements

### Requirement: Passada de glossário
O sistema SHALL, antes da tradução, extrair de uma amostra do livro os termos do domínio e nomes próprios, gerando um glossário (termo original → tradução) persistido como arquivo JSON editável à mão. O glossário SHALL ser incluído no contexto de todas as traduções.

#### Scenario: Glossário gerado e aplicado
- **WHEN** o usuário traduz um livro de computação
- **THEN** o sistema gera um glossário com os termos técnicos e o usa no contexto, de modo que o mesmo termo seja traduzido consistentemente ao longo do livro

#### Scenario: Glossário editado manualmente
- **WHEN** o usuário edita o arquivo JSON do glossário antes de traduzir
- **THEN** a tradução respeita as entradas editadas

### Requirement: Passada de priming
O sistema SHALL, antes da tradução, produzir um resumo do estilo e tom do livro a partir dos primeiros capítulos e SHALL usá-lo como contexto de estilo em todas as traduções.

#### Scenario: Tom consistente
- **WHEN** um livro possui estilo informal ou formal característico
- **THEN** a tradução mantém esse estilo ao longo de todo o livro

### Requirement: Política de termos técnicos
O sistema SHALL oferecer uma política configurável para termos técnicos: traduzir (ex.: `fila` para queue), manter em inglês (ex.: `queue`) ou híbrido (primeira ocorrência traduzida + termo original). O default SHALL ser híbrido.

#### Scenario: Política híbrida aplicada
- **WHEN** a política é híbrida e um termo técnico ocorre no livro
- **THEN** o termo aparece traduzido com o original preservado conforme a política, em todo o livro

### Requirement: Tradução em lotes
O sistema SHALL agrupar blocos em lotes que respeitem os limites de contexto do modelo e reduzam o overhead de chamadas, e SHALL traduzir lotes em paralelo conforme o paralelismo configurado.

#### Scenario: Livro longo
- **WHEN** um livro possui muitos capítulos
- **THEN** a tradução acontece em lotes paralelos, com progresso mensurável por bloco

### Requirement: Preservação de placeholders na saída
O sistema SHALL verificar, após cada lote, que todos os placeholders de conteúdo protegido retornaram intactos; divergências SHALL ser tratadas como falha do bloco (retry).

#### Scenario: Placeholder corrompido
- **WHEN** uma resposta não reproduz fielmente um placeholder de código
- **THEN** o bloco é reprocessado, e o código nunca é alterado na saída

### Requirement: Apêndice de glossário
O sistema SHALL adicionar ao livro traduzido um apêndice com o glossário de termos (original → tradução) usado na tradução.

#### Scenario: Livro com apêndice
- **WHEN** a tradução termina
- **THEN** o EPUB de saída contém um apêndice de termos técnicos com as entradas original → tradução

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
