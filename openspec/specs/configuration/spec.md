# configuration Specification

## Purpose

Centraliza as opções do usuário em um arquivo de configuração no diretório padrão de cada plataforma — providers, idiomas, política de termos, tabela de preços, teto de gasto e paralelismo — com defaults sensatos e validação clara.

## Requirements

### Requirement: Localização do arquivo de configuração
O sistema SHALL ler a configuração de um arquivo no diretório padrão da plataforma: `%APPDATA%` (Windows), `~/Library/Application Support` (macOS) e `~/.config` (Linux), usando o nome do aplicativo.

#### Scenario: Configuração encontrada
- **WHEN** o arquivo de configuração existe no diretório padrão da plataforma
- **THEN** o sistema carrega as opções do arquivo

#### Scenario: Primeira execução sem arquivo
- **WHEN** não existe arquivo de configuração
- **THEN** o sistema opera com os defaults e cria o arquivo quando o usuário salva configurações

### Requirement: Schema de configuração
O arquivo de configuração SHALL suportar família e provider selecionados, configurações específicas de LLM ou tradução automática, idiomas, política de termos, custo, teto de gasto, limites de lote, atraso e paralelismo. Configurações de provider SHALL poder declarar endpoint/variante sem guardar credenciais de usuário em texto puro.

#### Scenario: Configuração completa
- **WHEN** o usuário preenche todas as seções do exemplo
- **THEN** o sistema aplica todas as opções configuradas

#### Scenario: Configuração LLM
- **WHEN** o usuário salva um provider da família LLM
- **THEN** o arquivo preserva provider, modelo e endpoint compatível, sem chave de API

#### Scenario: Configuração Google Web
- **WHEN** o usuário salva Google Web
- **THEN** a configuração registra a família e o perfil do provider, sem exigir campo de chave de API ou modelo

### Requirement: Defaults sensatos
O sistema SHALL manter os defaults atuais para LLMs e SHALL fornecer defaults seguros para providers comuns, incluindo concorrência conservadora e limites de lote que reduzam risco de bloqueio.

#### Scenario: Uso sem configuração
- **WHEN** o usuário traduz sem alterar a configuração
- **THEN** os defaults acima são aplicados

#### Scenario: Primeiro uso do Google Web
- **WHEN** o usuário seleciona Google Web sem configuração anterior
- **THEN** o provider usa seus defaults experimentais sem pedir credencial

### Requirement: Validação de configuração
O sistema SHALL validar opções específicas da família/provider e informar campos inválidos sem iniciar a tradução.

#### Scenario: Configuração inválida
- **WHEN** o arquivo de configuração contém um valor inválido (ex.: paralelismo zero)
- **THEN** o sistema informa o campo específico e o valor aceito, sem iniciar a tradução

#### Scenario: Campo incompatível
- **WHEN** uma configuração comum contém opção exclusiva de LLM ou um limite inválido
- **THEN** o sistema aponta o campo e impede a execução

### Requirement: Chaves fora do arquivo de configuração
O arquivo de configuração SHALL nunca conter chaves de API em texto puro; chaves pertencem à porta de segredos.

#### Scenario: Configuração sem segredos
- **WHEN** o sistema grava o arquivo de configuração
- **THEN** nenhuma chave de API é gravada no arquivo
