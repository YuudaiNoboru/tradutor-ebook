# translation-cache Specification

## Purpose

Evita pagar duas vezes pela mesma tradução: cada bloco é armazenado em cache com uma chave completa de invalidação, e traduções interrompidas retomam exatamente de onde pararam.

## Requirements

### Requirement: Cache por bloco com chave completa
O sistema SHALL armazenar a tradução de cada bloco em cache cuja chave considera conteúdo do livro, família do provider, identidade do provider e variante do endpoint, idioma de origem, idioma de destino e os parâmetros de qualidade aplicáveis. Para LLMs, a chave SHALL incluir modelo, política e versão do glossário; para providers comuns, a chave SHALL omitir parâmetros não aplicáveis como glossário e priming.

#### Scenario: Dois idiomas no mesmo livro
- **WHEN** o mesmo livro é traduzido para pt-BR e depois para espanhol
- **THEN** as traduções não se misturam no cache e cada idioma é traduzido integralmente

#### Scenario: Mudança de modelo
- **WHEN** o usuário troca o modelo e re-traduz o livro
- **THEN** os blocos são re-traduzidos com o novo modelo, sem reaproveitar o cache do modelo anterior

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

#### Scenario: Interrupção por falha de rede
- **WHEN** a tradução falha no capítulo 20 de 40
- **THEN** ao retomar, os capítulos 1 a 19 são reaproveitados do cache e a tradução continua do capítulo 20

#### Scenario: Cancelamento manual
- **WHEN** o usuário cancela a tradução no meio
- **THEN** o progresso é preservado e a retomada posterior continua de onde parou

#### Scenario: Interrupção de provider comum
- **WHEN** o Google Web falha após concluir parte do livro
- **THEN** uma nova execução reaproveita os blocos válidos e continua nos pendentes

### Requirement: Cache corrompido não bloqueia
O sistema SHALL ignorar entradas de cache corrompidas ou incompatíveis para qualquer família de provider e re-traduzir somente os blocos afetados.

#### Scenario: Cache parcialmente corrompido
- **WHEN** algumas entradas do cache estão corrompidas
- **THEN** os blocos correspondentes são re-traduzidos e o restante é reaproveitado

#### Scenario: Cache com uso não mensurável
- **WHEN** uma entrada de provider comum não contém tokens
- **THEN** ela continua válida se a chave e a tradução estiverem íntegras, sem ser interpretada como erro
