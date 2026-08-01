## Purpose

Guarda chaves de API criptografadas — no cofre do sistema operacional com fallback de arquivo cifrado — e garante que as chaves nunca vazem em logs nem atravessem o núcleo do domínio.

## ADDED Requirements

### Requirement: Armazenamento no cofre do sistema
O sistema SHALL armazenar chaves de API no cofre do sistema operacional por padrão: Credential Manager (Windows), Keychain (macOS) e libsecret (Linux).

#### Scenario: Chave salva no cofre
- **WHEN** o usuário configura a chave da DeepSeek na primeira execução
- **THEN** a chave é guardada no cofre do sistema e não é gravada em arquivos de configuração

### Requirement: Fallback de arquivo cifrado
Quando não há cofre do sistema disponível, o sistema SHALL armazenar a chave em arquivo cifrado (Fernet) protegido por senha-mestra digitada pelo usuário, mantida apenas na memória da sessão.

#### Scenario: Sem cofre disponível
- **WHEN** o sistema não encontra um cofre utilizável (ex.: Linux sem serviço secreto)
- **THEN** o sistema usa o arquivo cifrado e solicita a senha-mestra uma vez por sessão

### Requirement: Override por variável de ambiente
O sistema SHALL permitir fornecer a chave por variável de ambiente seguindo a convenção do provedor (ex.: `DEEPSEEK_API_KEY`), com precedência sobre o armazenamento.

#### Scenario: Chave via ambiente
- **WHEN** a variável de ambiente do provedor está definida
- **THEN** o sistema usa essa chave sem tocar no armazenamento persistente

### Requirement: Precedência de origem da chave
O sistema SHALL resolver a chave na ordem: variável de ambiente, cofre do sistema, arquivo cifrado, e, na falta de todos, solicitação interativa na interface.

#### Scenario: Nenhuma chave disponível
- **WHEN** não há chave em nenhuma origem
- **THEN** a interface guia o usuário para configurar a chave antes de traduzir

### Requirement: Redação de segredos
O sistema SHALL mascarar chaves em qualquer saída: logs, mensagens de erro, relatórios e telemetria. A chave SHALL nunca ser gravada no cache de tradução.

#### Scenario: Erro sem exposição da chave
- **WHEN** uma chamada de API falha e o erro é registrado em log
- **THEN** nenhuma chave ou segredo aparece no log, mesmo em modos de depuração

### Requirement: Separação do núcleo do domínio
O sistema SHALL expor o acesso a chaves apenas por uma porta de segredos usada pelos adapters de provedor; o núcleo do domínio nunca SHALL receber chaves.

#### Scenario: Domínio sem acesso a segredos
- **WHEN** qualquer execução do pipeline de tradução acontece
- **THEN** o código do núcleo não recebe nem armazena chaves
