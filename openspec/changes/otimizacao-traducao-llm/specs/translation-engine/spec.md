## MODIFIED Requirements

### Requirement: Passada de priming
O sistema SHALL executar a passada de priming (Guia de Estilo e Tom) somente quando o provider selecionado declarar suporte a contexto de estilo e o usuário mantiver ativa a opção de geração de glossário e guia de estilo. O resumo de tom resultante SHALL ser persistido em arquivo `priming.txt` no diretório de trabalho para reuso permanente em retomadas. Para providers de tradução automática, a passada SHALL ser omitida.

#### Scenario: Tom consistente
- **WHEN** um livro possui estilo informal ou formal característico
- **THEN** a tradução mantém esse estilo ao longo de todo o livro

#### Scenario: Priming com LLM
- **WHEN** um provider LLM suporta priming e a opção está habilitada
- **THEN** o estilo e o tom extraídos são enviados no contexto dos lotes e salvos em `priming.txt`

#### Scenario: Priming indisponível
- **WHEN** o provider não suporta priming ou a opção foi desativada pelo usuário
- **THEN** a tradução começa sem chamada de priming e sem erro de configuração

### Requirement: Tradução em lotes
O sistema SHALL agrupar blocos conforme os limites declarados pelo provider, usando tokens para LLMs e caracteres/itens para providers de tradução automática, respeitando o limite máximo de itens por lote (`max_batch_items = 10 a 15`) também para LLMs. O sistema SHALL respeitar a concorrência efetiva, limitada pelo menor valor entre o desejo do usuário, o teto do provider e o limite máximo global de 20 worker threads (`MAX_GLOBAL_PARALLELISM = 20`). O título e os rótulos do sumário SHALL ser traduzidos como blocos normais na fila principal de lotes.

#### Scenario: Livro longo
- **WHEN** um livro possui muitos capítulos
- **THEN** a tradução acontece em lotes paralelos de tamanho reduzido (10 a 15 itens por lote), com progresso mensurável por bloco e teto global de 20 threads

#### Scenario: Lote limitado por caracteres
- **WHEN** um provider comum declara limite de caracteres menor que o lote atual
- **THEN** o motor divide os blocos antes da requisição sem cortar conteúdo protegido

#### Scenario: Título e sumário na fila principal
- **WHEN** a tradução inicia
- **THEN** o título e os rótulos do sumário entram na fila principal de lotes como blocos normais e a gravação final do EPUB ocorre imediatamente ao concluir 100% da fila

### Requirement: Preservação de placeholders na saída
O sistema SHALL verificar, após cada lote, que todos os placeholders e tags de conteúdo protegido retornaram intactos; divergências ou falhas em blocos individuais SHALL resultar na aceitação imediata dos blocos válidos no cache (`estado.json`) e no re-enfileiramento seletivo apenas dos blocos problemáticos.

#### Scenario: Placeholder corrompido
- **WHEN** uma resposta de lote contém um bloco que não reproduz fielmente as tags ou placeholders
- **THEN** os blocos válidos do lote são salvos no cache e apenas o bloco corrompido é re-enfileirado para correção
