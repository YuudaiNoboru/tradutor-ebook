# release-management Specification

## Purpose

Define como o projeto versiona, documenta e publica releases: versionamento semântico calculado a partir de commits convencionais, changelog incremental como fonte única de novidades e publicação via tag git e GitHub Release — com fluxo obrigatório de pull requests na branch principal.

## Requirements

### Requirement: Versionamento semântico em fase 0.x
O projeto SHALL manter a versão no formato MAJOR.MINOR.PATCH, com fonte única no pacote e propagação automática para builds e instalação. Enquanto MAJOR for 0, mudanças incompatíveis SHALL subir o número MINOR, nunca MAJOR.

#### Scenario: Nova funcionalidade
- **WHEN** uma release contém pelo menos uma nova funcionalidade
- **THEN** a versão sobe o número MINOR e o PATCH volta a zero (ex.: 0.2.3 → 0.3.0)

#### Scenario: Apenas correções
- **WHEN** uma release contém somente correções
- **THEN** a versão sobe apenas o número PATCH (ex.: 0.3.0 → 0.3.1)

#### Scenario: Mudança incompatível em fase 0.x
- **WHEN** uma release em fase 0.x contém mudança incompatível
- **THEN** a versão sobe o número MINOR (ex.: 0.3.1 → 0.4.0), permanecendo em MAJOR 0

### Requirement: Convenção de commits
Todo commit que entra na branch principal SHALL seguir o formato `type: description` com tipo reconhecido (ex.: `feat`, `fix`, `chore`, `docs`, `test`, `ci`), em que a descrição é livre em português. Títulos de pull request SHALL seguir a mesma convenção, pois o merge por squash converte o título no commit final.

#### Scenario: Commit conforme a convenção
- **WHEN** um commit com mensagem `feat: estimar custo antes de traduzir` entra na branch principal
- **THEN** ele é aceito e contabilizado para o cálculo da próxima versão

#### Scenario: Título de PR fora da convenção
- **WHEN** um pull request é aberto com título que não segue `type: description`
- **THEN** a verificação de título falha e o merge fica bloqueado

### Requirement: Barreira local de commits
Em um clone com a configuração do projeto aplicada, commits com mensagem fora da convenção SHALL ser recusados antes de serem criados.

#### Scenario: Commit recusado no clone
- **WHEN** o mantenedor tenta criar um commit com mensagem fora da convenção
- **THEN** o commit não é criado e a recusa indica o motivo

#### Scenario: Commit aceito no clone
- **WHEN** o mantenedor cria um commit com mensagem conforme a convenção
- **THEN** o commit é criado normalmente

### Requirement: Verificação de convenção no CI
O CI SHALL validar as mensagens dos commits que chegam à branch principal e o título de cada pull request, e SHALL expor um check agregador único que concentra o resultado de todas as verificações para fins de proteção de branch.

#### Scenario: PR com todos os checks verdes
- **WHEN** lint, testes, mensagens de commit e título do PR passam
- **THEN** o check agregador passa e o merge fica liberado

#### Scenario: Falha em qualquer verificação
- **WHEN** qualquer verificação do pull request falha
- **THEN** o check agregador não passa e o merge fica bloqueado

### Requirement: Fluxo PR-only na branch principal
A branch principal SHALL ser protegida: mudanças entram exclusivamente por pull request com verificações aprovadas, e o merge SHALL ser apenas por squash. Push direto na branch principal SHALL ser recusado, inclusive para o mantenedor.

#### Scenario: Push direto recusado
- **WHEN** qualquer pessoa tenta fazer push direto na branch principal
- **THEN** o servidor de hospedagem recusa o push

#### Scenario: Merge por squash
- **WHEN** um pull request com verificações aprovadas é mergado
- **THEN** exatamente um commit com o título do PR entra na branch principal

### Requirement: Changelog incremental
Cada release SHALL acrescentar ao CHANGELOG.md uma seção com a versão, contendo as entradas derivadas dos commits convencionais desde a release anterior; seções antigas SHALL ser preservadas. O changelog SHALL ser gerado automaticamente e nunca editado à mão.

#### Scenario: Nova seção na release
- **WHEN** uma release é preparada com novos `feat` e `fix` desde a última tag
- **THEN** o CHANGELOG.md recebe a seção da nova versão no topo, com as entradas correspondentes, mantendo as seções anteriores intactas

#### Scenario: Entradas refletem os commits
- **WHEN** o changelog é gerado
- **THEN** cada entrada corresponde à descrição de um commit convencional do período, agrupada por tipo com títulos em português

### Requirement: Publicação de release por tag
Uma release SHALL ser publicada quando uma tag anotada `v<versão>` for empurrada ao repositório: o sistema de CI SHALL criar a GitHub Release correspondente, cujas notas SHALL ser a seção daquela versão no CHANGELOG.md.

#### Scenario: Tag publica a release
- **WHEN** a tag `v0.2.0` é empurrada ao repositório
- **THEN** a GitHub Release `v0.2.0` é criada com as notas extraídas da seção correspondente do CHANGELOG.md

#### Scenario: Release sem seção no changelog
- **WHEN** uma tag é empurrada sem seção correspondente no CHANGELOG.md
- **THEN** a GitHub Release é criada mesmo assim, com notas vazias

### Requirement: Release por decisão explícita
Releases SHALL ocorrer apenas por decisão explícita do mantenedor, nunca automaticamente a cada merge. A preparação de release SHALL acontecer em um pull request próprio que atualiza versão e changelog.

#### Scenario: Merge comum não libera release
- **WHEN** um pull request com funcionalidades é mergado na branch principal
- **THEN** nenhuma versão nova nem tag é criada

#### Scenario: Pull request de release
- **WHEN** o mantenedor prepara uma release em branch própria e o respectivo pull request é mergado
- **THEN** a branch principal passa a conter a versão e o changelog atualizados, prontos para a tag

### Requirement: Guia para agentes de IA
O repositório SHALL manter um arquivo de regras de fluxo para agentes de IA como fonte única de verdade, e cada ferramenta de IA suportada pelo projeto SHALL ter um arquivo de instruções apontando para ele. O guia SHALL cobrir: proibição de push direto na branch principal, convenção de commits e títulos de PR, arquivos que nunca devem ser editados manualmente (versão e changelog) e o fluxo de release sob pedido do usuário.

#### Scenario: Agente inicia sessão no repositório
- **WHEN** qualquer ferramenta de IA suportada abre o repositório
- **THEN** ela carrega as regras de fluxo a partir do arquivo de instruções correspondente
