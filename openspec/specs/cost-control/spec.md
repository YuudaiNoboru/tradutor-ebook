# cost-control Specification

## Purpose

Dá ao usuário controle financeiro sobre o uso de LLM: estimativa de custo antes da tradução (em US$, moeda das APIs), aviso de que é estimativa, teto de gasto opcional e relatório de custo real comparado ao previsto.

## Requirements

### Requirement: Estimativa pré-voo
O sistema SHALL apresentar, antes de iniciar a tradução, uma estimativa de custo baseada no payload real de texto traduzível (blocos protegidos excluídos): tokens de entrada, tokens de saída estimados (fator de expansão do idioma alvo), custo estimado em US$ e tempo estimado.

#### Scenario: Estimativa exibida antes de traduzir
- **WHEN** o usuário seleciona um livro e confirma as configurações
- **THEN** a tela mostra tokens e custo estimados em US$ e o tempo estimado, e a tradução só começa após confirmação

#### Scenario: Código não entra na conta
- **WHEN** um livro possui muitos blocos de código
- **THEN** a estimativa considera apenas o texto que será efetivamente enviado ao modelo

### Requirement: Aviso de estimativa e recomendação de limite
A tela de estimativa SHALL declarar explicitamente que o valor é uma estimativa e SHALL recomendar a configuração de limites de gasto na conta do provedor da chave em uso.

#### Scenario: Aviso presente na confirmação
- **WHEN** a tela de estimativa é exibida
- **THEN** o texto de aviso informa que o valor é estimativa e recomenda limites na conta do provider

### Requirement: Teto de gasto
O sistema SHALL suportar um teto de gasto configurável (US$); quando o custo real acumulado ultrapassa o teto, a tradução SHALL parar com aviso claro. Sem teto configurado, a tradução prossegue normalmente.

#### Scenario: Teto atingido durante a tradução
- **WHEN** o custo real acumulado ultrapassa o teto configurado
- **THEN** a tradução para imediatamente com aviso, e o progresso permanece no cache para retomada com novo teto

#### Scenario: Sem teto configurado
- **WHEN** nenhum teto está configurado
- **THEN** a tradução prossegue normalmente até o fim

### Requirement: Relatório real vs previsto
Ao final, o sistema SHALL apresentar um relatório com o custo e os tokens reais (somados a partir do uso reportado pela API) comparados à estimativa inicial.

#### Scenario: Relatório final
- **WHEN** a tradução termina
- **THEN** o relatório mostra custo real em US$, tokens reais e a comparação com o previsto

### Requirement: Tabela de preços editável
O sistema SHALL manter os preços por provider/modelo (entrada e saída por milhão de tokens) em uma tabela editável na configuração, usada pela estimativa.

#### Scenario: Preços atualizados
- **WHEN** o usuário atualiza os preços no arquivo de configuração
- **THEN** as estimativas subsequentes usam os novos valores
