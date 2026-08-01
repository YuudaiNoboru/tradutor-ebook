## Purpose

Evita pagar duas vezes pela mesma tradução: cada bloco é armazenado em cache com uma chave completa de invalidação, e traduções interrompidas retomam exatamente de onde pararam.

## ADDED Requirements

### Requirement: Cache por bloco com chave completa
O sistema SHALL armazenar a tradução de cada bloco em cache cuja chave considera: conteúdo do livro, idioma de origem, idioma de destino, modelo, política de termos e versão do glossário.

#### Scenario: Dois idiomas no mesmo livro
- **WHEN** o mesmo livro é traduzido para pt-BR e depois para espanhol
- **THEN** as traduções não se misturam no cache e cada idioma é traduzido integralmente

#### Scenario: Mudança de modelo
- **WHEN** o usuário troca o modelo e re-traduz o livro
- **THEN** os blocos são re-traduzidos com o novo modelo, sem reaproveitar o cache do modelo anterior

### Requirement: Retomada de tradução interrompida
O sistema SHALL permitir que uma tradução interrompida (rede, limite da API, cancelamento, queda do processo) seja retomada sem re-traduzir os blocos já concluídos.

#### Scenario: Interrupção por falha de rede
- **WHEN** a tradução falha no capítulo 20 de 40
- **THEN** ao retomar, os capítulos 1 a 19 são reaproveitados do cache e a tradução continua do capítulo 20

#### Scenario: Cancelamento manual
- **WHEN** o usuário cancela a tradução no meio
- **THEN** o progresso é preservado e a retomada posterior continua de onde parou

### Requirement: Cache corrompido não bloqueia
O sistema SHALL ignorar entradas de cache corrompidas ou ilegíveis, re-traduzindo os blocos afetados sem interromper a execução.

#### Scenario: Cache parcialmente corrompido
- **WHEN** algumas entradas do cache estão corrompidas
- **THEN** os blocos correspondentes são re-traduzidos e o restante é reaproveitado
