## MODIFIED Requirements

### Requirement: Estimativa pré-voo
O sistema SHALL apresentar, antes da tradução, uma estimativa adequada ao provider selecionado. Para LLMs, SHALL exibir tokens, custo em US$ e tempo; para providers sem medição de tokens ou cobrança por credencial do usuário, SHALL exibir caracteres/blocos, custo como não mensurável ou não aplicável e tempo estimado.

#### Scenario: Estimativa LLM
- **WHEN** o usuário seleciona um provider LLM com preços configurados
- **THEN** a tela exibe tokens e custo estimados em US$

#### Scenario: Estimativa Google Web
- **WHEN** o usuário seleciona Google Web
- **THEN** a tela não apresenta zero tokens como se nenhum conteúdo fosse processado e informa que o serviço não fornece medição de uso

### Requirement: Aviso de estimativa e recomendação de limite
A tela de estimativa SHALL explicar a natureza da medição do provider. Para LLMs, SHALL recomendar limites de gasto na conta da chave; para providers comuns gratuitos, SHALL informar que não há custo mensurável pelo aplicativo, mas existem limites e bloqueios do serviço remoto.

#### Scenario: Aviso de provider comum
- **WHEN** a estimativa é exibida para um provider gratuito
- **THEN** o aviso menciona limites, instabilidade e ausência de garantia de gratuidade futura

### Requirement: Relatório real vs previsto
Ao final, o sistema SHALL apresentar um relatório compatível com a telemetria do provider: tokens e custo real para LLMs; caracteres/blocos processados e custo/uso não reportado para providers comuns.

#### Scenario: Relatório Google Web
- **WHEN** uma tradução Google Web termina
- **THEN** o relatório informa blocos concluídos e que o endpoint não reportou tokens ou custo

### Requirement: Tabela de preços editável
O sistema SHALL manter preços somente para providers/modelos que possuam cobrança mensurável configurável. Providers comuns sem cobrança reportada SHALL poder declarar ausência de tabela de preços sem impedir a tradução.

#### Scenario: Provider sem preço
- **WHEN** o provider selecionado não possui preço configurado
- **THEN** a estimativa não bloqueia a execução por falta de preço e exibe a medição como não aplicável
