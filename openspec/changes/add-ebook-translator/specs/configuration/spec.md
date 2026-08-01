## Purpose

Centraliza as opções do usuário em um arquivo de configuração no diretório padrão de cada plataforma — providers, idiomas, política de termos, tabela de preços, teto de gasto e paralelismo — com defaults sensatos e validação clara.

## ADDED Requirements

### Requirement: Localização do arquivo de configuração
O sistema SHALL ler a configuração de um arquivo no diretório padrão da plataforma: `%APPDATA%` (Windows), `~/Library/Application Support` (macOS) e `~/.config` (Linux), usando o nome do aplicativo.

#### Scenario: Configuração encontrada
- **WHEN** o arquivo de configuração existe no diretório padrão da plataforma
- **THEN** o sistema carrega as opções do arquivo

#### Scenario: Primeira execução sem arquivo
- **WHEN** não existe arquivo de configuração
- **THEN** o sistema opera com os defaults e cria o arquivo quando o usuário salva configurações

### Requirement: Schema de configuração
O arquivo de configuração SHALL suportar: provider padrão, providers (modelo, `base_url`; sem chaves), tradução (origem, destino, política de termos), custo (tabela de preços por provider/modelo, teto de gasto em US$) e execução (paralelismo). Um `config.example.toml` SHALL ser versionado no repositório como referência.

#### Scenario: Configuração completa
- **WHEN** o usuário preenche todas as seções do exemplo
- **THEN** o sistema aplica todas as opções configuradas

### Requirement: Defaults sensatos
O sistema SHALL usar como padrão: destino `pt-BR`, origem com detecção automática, política de termos híbrida, paralelismo 4 e teto de gasto desligado.

#### Scenario: Uso sem configuração
- **WHEN** o usuário traduz sem alterar a configuração
- **THEN** os defaults acima são aplicados

### Requirement: Validação de configuração
O sistema SHALL validar o arquivo de configuração e, em caso de erro, SHALL apresentar mensagem clara indicando o campo e o problema.

#### Scenario: Configuração inválida
- **WHEN** o arquivo de configuração contém um valor inválido (ex.: paralelismo zero)
- **THEN** o sistema informa o campo específico e o valor aceito, sem iniciar a tradução

### Requirement: Chaves fora do arquivo de configuração
O arquivo de configuração SHALL nunca conter chaves de API em texto puro; chaves pertencem à porta de segredos.

#### Scenario: Configuração sem segredos
- **WHEN** o sistema grava o arquivo de configuração
- **THEN** nenhuma chave de API é gravada no arquivo
