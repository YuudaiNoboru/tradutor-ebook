# engineering-harness Specification

## Purpose

Provê um ecossistema determinístico de controle de qualidade, fitness functions arquiteturais, checagem estrita de tipos, testes de mutação e validações contínuas de segurança para o ciclo de desenvolvimento do tradutor-ebook.

## Requirements

### Requirement: Static Type Safety Enforcement
O sistema de desenvolvimento e CI DEVE executar a checagem estrita de tipos estáticos em todos os módulos de `src/` e `tests/` e rejeitar qualquer incompatibilidade ou omissão de tipos.

#### Scenario: Typecheck com sucesso
- **WHEN** o desenvolvedor ou CI executa o comando de typecheck em uma base de código com tipagem estrita válida
- **THEN** o verificador conclui com código de saída 0 e sem emissão de erros de tipo

#### Scenario: Falha de tipagem estática
- **WHEN** um módulo introduz parâmetros ou retornos sem tipos ou passa tipos incompatíveis
- **THEN** o verificador falha com código de saída diferente de zero e aponta exatamente o arquivo e linha da inconsistência

### Requirement: Hexagonal Architecture Fitness Verification
O sistema DEVE validar deterministicamente que o módulo `src/tradutor/domain` não importa direta ou indiretamente adaptadores de infraestrutura, interfaces de usuário, manipuladores de EPUB ou orquestradores.

#### Scenario: Isolamento puro do domínio
- **WHEN** a suíte de validação de arquitetura é executada e o domínio depende apenas de tipos primitivos e módulos puros
- **THEN** o verificador de arquitetura é aprovado com sucesso

#### Scenario: Violação de fronteira arquitetural
- **WHEN** um arquivo dentro de `src/tradutor/domain` tenta importar qualquer símbolo de `src/tradutor/tui`, `src/tradutor/infra` ou `src/tradutor/epub`
- **THEN** o verificador de arquitetura rejeita a execução e emite a árvore de importação causadora da violação

### Requirement: Local Pre-commit Quality Gate
O repositório DEVE disponibilizar um hook Git `pre-commit` nativo gerenciado por comando de setup que executa linter, checagem de formatação e verificação de tipos antes de permitir a criação de um commit.

#### Scenario: Commit com código fora do padrão
- **WHEN** o desenvolvedor tenta commitar arquivos com erros de formatação ou lint
- **THEN** o hook cancela a operação de commit e orienta a execução dos comandos de autocorreção

#### Scenario: Commit em conformidade
- **WHEN** os arquivos staged passam em todas as checagens estáticas locais
- **THEN** o hook permite que o fluxo do Git prossiga para a validação da mensagem de commit

### Requirement: Semantic Mutation Testing for Critical Markup Modules
O sistema DEVE disponibilizar comandos para execução de testes de mutação nos 4 módulos críticos de integridade de markup e sanitização (`domain/protection.py`, `domain/quality.py`, `epub/segments.py`, `epub/index_rebuilder.py`).

#### Scenario: Execução de mutação em módulos críticos
- **WHEN** o comando de mutação é disparado para os módulos críticos
- **THEN** o executor introduz mutações no código e valida que a suíte de testes mata os mutantes gerando um relatório sem sobreviventes nos fluxos principais

### Requirement: Dependency Vulnerability Audit
O sistema DEVE auditar as dependências de terceiros contra bancos de vulnerabilidades conhecidas (CVEs) em ambiente local e no pipeline de CI.

#### Scenario: Verificação de vulnerabilidades em PR
- **WHEN** o pipeline de CI executa o passo de auditoria de dependências
- **THEN** qualquer pacote com vulnerabilidade reportada bloqueia o avanço do gate agregador

### Requirement: Dead Code and Unused Slices Detection
O sistema DEVE inspecionar a base de código em busca de funções, classes ou variáveis declaradas e nunca referenciadas, respeitando listas de exceções declarativas para callbacks e hooks da TUI.

#### Scenario: Verificação de código morto
- **WHEN** o comando de detecção de dead code é executado
- **THEN** símbolos não utilizados são listados com seus caminhos e linhas correspondentes

### Requirement: E2E Asynchronous TUI Simulation
A suíte de testes DEVE conter testes de ponta a ponta assíncronos que inicializam e exercitam as telas da TUI via Textual Pilot sem abrir janelas reais de terminal.

#### Scenario: Simulação de fluxo de navegação na TUI
- **WHEN** o teste E2E executa a aplicação simulada e navega pelas telas principais
- **THEN** os eventos de transição, focagem e atualização de estado reativo são disparados e verificados com asserções assíncronas

### Requirement: Extensibility Guide for New Providers
O repositório DEVE fornecer um guia declarativo e padronizado em `docs/guias/novo-provedor.md` contendo as regras de contrato, tratamento de rate limit e checklist para implementação de novos provedores de tradução.

#### Scenario: Consulta ao guia de novos provedores
- **WHEN** um desenvolvedor ou agente consulta a documentação para adicionar um novo provedor
- **THEN** o documento fornece o contrato da classe abstrata, tratamento de erros esperado e passos para registro na factory
