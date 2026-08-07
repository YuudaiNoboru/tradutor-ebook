## MODIFIED Requirements

### Requirement: Tela de configuração
O sistema SHALL oferecer tela de configuração em português com seleção inicial da família de provider e, em seguida, seleção do provider disponível. A tela SHALL exibir somente campos compatíveis: credencial e modelo para LLMs quando necessários; perfil, limites e avisos para tradutores comuns. Idiomas e paralelismo SHALL permanecer configuráveis conforme as capacidades do provider.

#### Scenario: Selecionar família LLM
- **WHEN** o usuário escolhe LLMs
- **THEN** a UI exibe providers/modelos LLM, campo de chave mascarado e opções de glossário/priming aplicáveis

#### Scenario: Selecionar família comum
- **WHEN** o usuário escolhe tradutores automáticos
- **THEN** a UI exibe Google Web, não pede chave/modelo e informa que glossário, priming e política de termos não se aplicam

### Requirement: Teste de conexão
O sistema SHALL testar o provider e seu perfil atualmente selecionados. Para providers sem rota de modelos, SHALL executar uma verificação compatível com o endpoint e não exigir listagem de modelos para considerar a conexão válida.

#### Scenario: Teste Google Web
- **WHEN** o usuário testa Google Web com idiomas válidos
- **THEN** a UI confirma ou explica a falha do endpoint sem solicitar credencial

### Requirement: Ajuda
Ao acionar a ajuda, o sistema SHALL explicar BYOK para LLMs e SHALL explicar para providers comuns a ausência de chave do usuário, o uso de endpoints não oficiais, a ausência de glossário/priming, a preservação de conteúdo, a instabilidade, os limites, a privacidade e a retomada por cache.

#### Scenario: Ajuda sobre provider gratuito
- **WHEN** o usuário abre a ajuda após selecionar Google Web
- **THEN** encontra as limitações antes de iniciar uma tradução

### Requirement: Estimativa e confirmação
Antes de iniciar, o sistema SHALL exibir uma confirmação adaptada à família/provider, incluindo preservação de formatação e medição de custo/uso compatível.

#### Scenario: Confirmação de tradução comum
- **WHEN** o usuário confirma uma tradução Google Web
- **THEN** vê aviso de serviço experimental, limites remotos, ausência de custo/token mensurável e confirmação de que a estrutura XHTML será validada
