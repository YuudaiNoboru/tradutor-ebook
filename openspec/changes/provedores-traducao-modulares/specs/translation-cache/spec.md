## MODIFIED Requirements

### Requirement: Cache por bloco com chave completa
O sistema SHALL armazenar a tradução de cada bloco em cache cuja chave considera conteúdo do livro, família do provider, identidade do provider e variante do endpoint, idioma de origem, idioma de destino e os parâmetros de qualidade aplicáveis. Para LLMs, a chave SHALL incluir modelo, política e versão do glossário; para providers comuns, a chave SHALL omitir parâmetros não aplicáveis como glossário e priming.

#### Scenario: Troca de família
- **WHEN** o mesmo EPUB é traduzido primeiro com LLM e depois com Google Web
- **THEN** o segundo fluxo não reutiliza traduções da primeira família

#### Scenario: Mudança de variante do Google
- **WHEN** o endpoint ou perfil de resposta do Google é alterado
- **THEN** a chave de cache muda e os blocos afetados não são tratados como traduções compatíveis

#### Scenario: Mudança de modelo LLM
- **WHEN** o usuário troca o modelo LLM
- **THEN** os blocos são re-traduzidos com o novo modelo

### Requirement: Retomada de tradução interrompida
O sistema SHALL permitir que qualquer provider retome uma tradução interrompida sem re-traduzir blocos já concluídos e compatíveis com a chave atual.

#### Scenario: Interrupção de provider comum
- **WHEN** o Google Web falha após concluir parte do livro
- **THEN** uma nova execução reaproveita os blocos válidos e continua nos pendentes

### Requirement: Cache corrompido não bloqueia
O sistema SHALL ignorar entradas de cache corrompidas ou incompatíveis para qualquer família de provider e re-traduzir somente os blocos afetados.

#### Scenario: Cache com uso não mensurável
- **WHEN** uma entrada de provider comum não contém tokens
- **THEN** ela continua válida se a chave e a tradução estiverem íntegras, sem ser interpretada como erro
