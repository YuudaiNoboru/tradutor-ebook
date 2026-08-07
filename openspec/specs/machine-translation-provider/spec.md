# machine-translation-provider Specification

## Purpose
Oferece tradução automática tradicional por providers modulares, começando pelo Google Web gratuito, preservando rigorosamente a estrutura e a formatação dos blocos XHTML do EPUB.

## Requirements

### Requirement: Porta de tradução automática
O sistema SHALL expor uma porta distinta da porta de LLM para providers de tradução automática. A porta SHALL receber blocos, idioma de origem e idioma de destino, e SHALL retornar uma tradução alinhada a cada bloco sem receber glossário, priming ou política de termos.

#### Scenario: Tradução comum sem contexto de LLM
- **WHEN** o motor envia blocos a um provider de tradução automática
- **THEN** o provider traduz somente o conteúdo e os idiomas informados, sem executar glossário, priming ou apêndice de glossário

### Requirement: Capacidades declaradas pelo provider
Cada provider SHALL declarar sua família, estabilidade, necessidade de credenciais, suporte a HTML, limites de lote, medição de uso e suporte a listagem de modelos.

#### Scenario: UI consulta capacidades
- **WHEN** a UI seleciona um provider de tradução automática
- **THEN** exibe somente controles compatíveis com as capacidades declaradas

### Requirement: Provider Google Web gratuito
O sistema SHALL oferecer o Google Web como provider experimental sem exigir uma credencial do usuário, usando o endpoint HTML da interface web e uma alternativa de texto quando o fluxo HTML falhar de forma compatível.

#### Scenario: Google traduz bloco XHTML
- **WHEN** o usuário seleciona Google Web e fornece um EPUB traduzível
- **THEN** o sistema envia o conteúdo do bloco ao endpoint configurado, interpreta a resposta alinhada e continua o fluxo de tradução

### Requirement: Preservação de formatação
O provider de tradução automática SHALL preservar tags XHTML inline, placeholders e conteúdo protegido exatamente como recebido; uma resposta que altere a sequência ou o conteúdo protegido SHALL ser rejeitada antes de entrar no cache ou no EPUB de saída.

#### Scenario: Provider altera uma tag
- **WHEN** a resposta remove, adiciona ou reordena uma tag inline ou placeholder protegido
- **THEN** o lote é considerado inválido, não é persistido e fica sujeito à política de retry/retomada

### Requirement: Limitação e recuperação de requisições
O provider SHALL dividir requisições por limites conservadores de caracteres e itens, limitar concorrência, respeitar atrasos configurados e repetir falhas transitórias com backoff e jitter. Falhas definitivas SHALL produzir erro acionável e preservar o progresso anterior.

#### Scenario: Rate limit temporário
- **WHEN** o endpoint retorna bloqueio ou erro transitório
- **THEN** o provider aguarda conforme a política, tenta novamente dentro do limite e, se esgotado, deixa os blocos pendentes para retomada

### Requirement: Transparência do provider experimental
O sistema SHALL informar que o provider usa endpoints não oficiais, não exige chave do usuário, pode mudar ou deixar de funcionar, não oferece glossário/priming e não fornece custo ou uso de tokens mensurável.

#### Scenario: Usuário escolhe Google Web
- **WHEN** a tela de configuração ou ajuda apresenta o provider
- **THEN** mostra suas limitações antes da tradução ser confirmada
