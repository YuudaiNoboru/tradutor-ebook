# cost-control Specification

## Purpose

Dá ao usuário controle financeiro sobre o uso de LLM: estimativa de custo antes da tradução (em US$, moeda das APIs), aviso de que é estimativa, teto de gasto opcional e relatório de custo real comparado ao previsto.

## Requirements

### Requirement: Estimativa pré-voo
O sistema SHALL apresentar, antes da tradução, uma estimativa adequada ao provider selecionado. Para LLMs, SHALL exibir tokens, custo em US$ e tempo; para providers sem medição de tokens ou cobrança por credencial do usuário, SHALL exibir caracteres/blocos, custo como não mensurável ou não aplicável e tempo estimado.

#### Scenario: Estimativa exibida antes de traduzir
- **WHEN** o usuário seleciona um livro e confirma as configurações
- **THEN** a tela mostra tokens e custo estimados em US$ e o tempo estimado, e a tradução só começa após confirmação

#### Scenario: Código não entra na conta
- **WHEN** um livro possui muitos blocos de código
- **THEN** a estimativa considera apenas o texto que será efetivamente enviado ao modelo

#### Scenario: Estimativa LLM
- **WHEN** o usuário seleciona um provider LLM com preços configurados
- **THEN** a tela exibe tokens e custo estimados em US$

#### Scenario: Estimativa Google Web
- **WHEN** o usuário seleciona Google Web
- **THEN** a tela não apresenta zero tokens como se nenhum conteúdo fosse processado e informa que o serviço não fornece medição de uso

### Requirement: Aviso de estimativa e recomendação de limite
A tela de estimativa SHALL explicar a natureza da medição do provider. Para LLMs, SHALL recomendar limites de gasto na conta da chave; para providers comuns gratuitos, SHALL informar que não há custo mensurável pelo aplicativo, mas existem limites e bloqueios do serviço remoto.

#### Scenario: Aviso presente na confirmação
- **WHEN** a tela de estimativa é exibida
- **THEN** o texto de aviso informa que o valor é estimativa e recomenda limites na conta do provider

#### Scenario: Aviso de provider comum
- **WHEN** a estimativa é exibida para um provider gratuito
- **THEN** o aviso menciona limites, instabilidade e ausência de garantia de gratuidade futura

### Requirement: Teto de gasto
O sistema SHALL suportar um teto de gasto configurável (US$); quando o custo real acumulado ultrapassa o teto, a tradução SHALL parar com aviso claro. Sem teto configurado, a tradução prossegue normalmente.

#### Scenario: Teto atingido durante a tradução
- **WHEN** o custo real acumulado ultrapassa o teto configurado
- **THEN** a tradução para imediatamente com aviso, e o progresso permanece no cache para retomada com novo teto

#### Scenario: Sem teto configurado
- **WHEN** nenhum teto está configurado
- **THEN** a tradução prossegue normalmente até o fim

### Requirement: Relatório real vs previsto
Ao final, o sistema SHALL apresentar um relatório compatível com a telemetria do provider: tokens e custo real para LLMs; caracteres/blocos processados e custo/uso não reportado para providers comuns.

#### Scenario: Relatório final
- **WHEN** a tradução termina
- **THEN** o relatório mostra custo real em US$, tokens reais e a comparação com o previsto

#### Scenario: Relatório Google Web
- **WHEN** uma tradução Google Web termina
- **THEN** o relatório informa blocos concluídos e que o endpoint não reportou tokens ou custo

### Requirement: Tabela de preços editável
O sistema SHALL manter preços somente para providers/modelos que possuam cobrança mensurável configurável. Providers comuns sem cobrança reportada SHALL poder declarar ausência de tabela de preços sem impedir a tradução.

#### Scenario: Preços atualizados
- **WHEN** o usuário atualiza os preços no arquivo de configuração
- **THEN** as estimativas subsequentes usam os novos valores

#### Scenario: Provider sem preço
- **WHEN** o provider selecionado não possui preço configurado
- **THEN** a estimativa não bloqueia a execução por falta de preço e exibe a medição como não aplicável
