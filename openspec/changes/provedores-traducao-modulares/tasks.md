## 1. Contratos de domínio e descoberta

- [x] 1.1 Definir os tipos de família de provider, capacidades declaradas e identidade versionada do provider
- [x] 1.2 Generalizar o resultado de tradução e o relatório de uso para tokens opcionais e contagem de caracteres/blocos
- [x] 1.3 Criar portas distintas para tradução LLM e tradução automática, com seus respectivos contextos e fábricas
- [x] 1.4 Implementar descoberta por módulos em `providers/llm/` e `providers/machine_translation/`, validando metadados e IDs duplicados
- [x] 1.5 Adicionar testes de contrato para capacidades, descoberta, rejeição de módulos inválidos e isolamento arquitetural

## 2. Migração dos providers LLM

- [x] 2.1 Organizar o adapter OpenAI-compatível e o provider DeepSeek sob a família LLM sem alterar o comportamento público existente
- [x] 2.2 Preservar aliases, defaults, seleção de modelo, autenticação por cofre e tratamento de erros do DeepSeek
- [x] 2.3 Adicionar um módulo LLM compatível de referência que possa ser descoberto sem editar um registro central
- [x] 2.4 Atualizar os testes do adapter e do fluxo LLM para a nova porta, mantendo glossário, priming, política e uso de tokens

## 3. Provider Google Web experimental

- [x] 3.1 Criar o pacote de tradução automática e o módulo de descrição/fábrica do Google Web, incluindo capacidades, limites e aviso experimental
- [x] 3.2 Implementar o transporte HTML com `httpx`, cliente injetável, timeout explícito, User-Agent e perfil de endpoint versionado
- [x] 3.3 Implementar o parser estrito das respostas HTML e o perfil textual de fallback, aceitando fallback apenas quando a preservação puder ser validada
- [x] 3.4 Encapsular URLs, variante do corpo, versão do parser e eventual override operacional sem tratar chave pública como segredo do usuário
- [x] 3.5 Implementar limites conservadores por caracteres/itens, concorrência efetiva, atraso configurável e backoff com jitter para falhas transitórias
- [x] 3.6 Classificar bloqueios, respostas incompatíveis e falhas definitivas em erros acionáveis, preservando os blocos já concluídos
- [x] 3.7 Criar testes com cliente HTTP falso e fixtures para sucesso HTML, fallback, respostas inválidas, rate limit, timeout, retry e esgotamento

## 4. Preservação de XHTML e EPUB

- [x] 4.1 Integrar a porta comum à segmentação existente, mantendo `code`, `pre`, SVG, MathML, script, style e placeholders fora do conteúdo traduzível
- [x] 4.2 Validar alinhamento, tags inline, placeholders, conteúdo não vazio e reconstrução antes de aceitar cada resposta de provider
- [x] 4.3 Impedir cache e gravação no EPUB quando uma tradução alterar markup ou conteúdo protegido
- [x] 4.4 Adicionar fixtures douradas EPUB 2/3 e testes byte-diff para confirmar arquivos intocados e preservação dos blocos protegidos
- [x] 4.5 Cobrir no teste de integração a retomada após falha de provider sem gravar uma saída parcialmente inválida

## 5. Orquestração por capacidades

- [x] 5.1 Alterar o orquestrador para consultar capacidades antes das passadas e omitir glossário, priming, política e apêndice quando não aplicáveis
- [x] 5.2 Adaptar o agrupamento de lotes para usar tokens em LLMs e caracteres/itens em providers comuns, sem cortar conteúdo protegido
- [x] 5.3 Respeitar a concorrência e os limites declarados pelo provider ao submeter lotes
- [x] 5.4 Manter o fluxo de glossário, priming, política de termos e apêndice inalterado para LLMs compatíveis
- [x] 5.5 Garantir que providers comuns não criem glossário, não exijam seus arquivos e não adicionem apêndice ao EPUB
- [x] 5.6 Adicionar testes unitários e end-to-end para seleção de família, passadas condicionais, lotes e retomada

## 6. Cache, estimativa e relatório de custo

- [x] 6.1 Expandir a chave de cache com família, provider e variante de transporte, mantendo modelo/política/glossário somente quando aplicáveis
- [x] 6.2 Implementar compatibilidade conservadora para estados antigos do DeepSeek e invalidar chaves ambíguas sem interromper a execução
- [x] 6.3 Atualizar validação de entradas corrompidas e retomada para aceitar uso não mensurável sem confundi-lo com cache inválido
- [x] 6.4 Generalizar estimativa, teto e relatório para custo mensurável de LLM e caracteres/blocos com custo/uso não reportado
- [x] 6.5 Garantir que provider sem tabela de preços não bloqueie a tradução e exiba aviso de limites e instabilidade remotos
- [x] 6.6 Adicionar testes de isolamento entre famílias/variantes, migração, corrupção de cache e relatório previsto-versus-real

## 7. Configuração e segurança

- [x] 7.1 Evoluir o schema TOML para família, provider, variante, idiomas, limites, atraso e paralelismo, preservando configurações antigas
- [x] 7.2 Implementar defaults seguros do Google Web e validação de campos incompatíveis ou limites inválidos
- [x] 7.3 Ajustar leitura/escrita para não persistir chaves de usuário e não exigir credencial para provider comum
- [x] 7.4 Manter override por ambiente, keyring/cofre e redação de logs para LLMs sem expor segredos ao núcleo do domínio
- [x] 7.5 Atualizar `config.example.toml` e os testes de carga, serialização, defaults, compatibilidade e validação

## 8. TUI e documentação de uso

- [x] 8.1 Alterar a tela de configuração para selecionar primeiro a família e depois exibir somente providers e controles compatíveis
- [x] 8.2 Ocultar chave, modelo, glossário e priming para Google Web e exibir perfil, limites, atraso e aviso experimental
- [x] 8.3 Adaptar teste de conexão para providers com listagem de modelos e para providers que só possuem endpoint de tradução
- [x] 8.4 Adaptar estimativa, confirmação, progresso e relatório para medição de tokens ou caracteres/blocos conforme as capacidades
- [x] 8.5 Atualizar ajuda e mensagens em pt-BR com BYOK, endpoints não oficiais, privacidade, limitações, bloqueios e retomada por cache
- [x] 8.6 Criar testes de fluxo da TUI para troca de família, validação, conexão, confirmação e apresentação dos avisos

## 9. Validação e entrega

- [x] 9.1 Atualizar README e documentação de configuração com o provider experimental, suas limitações e a ausência de garantia de disponibilidade/gratuidade
- [x] 9.2 Executar smoke test manual contra os endpoints reais fora do CI e registrar a variante validada sem incluir credenciais ou conteúdo do livro
- [x] 9.3 Executar `hatch run lint`, `hatch run fmt-check` e `hatch run cov`, corrigindo regressões até manter o gate de cobertura verde



