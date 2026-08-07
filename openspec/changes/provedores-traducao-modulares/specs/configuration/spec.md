## MODIFIED Requirements

### Requirement: Schema de configuração
O arquivo de configuração SHALL suportar família e provider selecionados, configurações específicas de LLM ou tradução automática, idiomas, política de termos, custo, teto de gasto, limites de lote, atraso e paralelismo. Configurações de provider SHALL poder declarar endpoint/variante sem guardar credenciais de usuário em texto puro.

#### Scenario: Configuração LLM
- **WHEN** o usuário salva um provider da família LLM
- **THEN** o arquivo preserva provider, modelo e endpoint compatível, sem chave de API

#### Scenario: Configuração Google Web
- **WHEN** o usuário salva Google Web
- **THEN** a configuração registra a família e o perfil do provider, sem exigir campo de chave de API ou modelo

### Requirement: Defaults sensatos
O sistema SHALL manter os defaults atuais para LLMs e SHALL fornecer defaults seguros para providers comuns, incluindo concorrência conservadora e limites de lote que reduzam risco de bloqueio.

#### Scenario: Primeiro uso do Google Web
- **WHEN** o usuário seleciona Google Web sem configuração anterior
- **THEN** o provider usa seus defaults experimentais sem pedir credencial

### Requirement: Validação de configuração
O sistema SHALL validar opções específicas da família/provider e informar campos inválidos sem iniciar a tradução.

#### Scenario: Campo incompatível
- **WHEN** uma configuração comum contém opção exclusiva de LLM ou um limite inválido
- **THEN** o sistema aponta o campo e impede a execução
