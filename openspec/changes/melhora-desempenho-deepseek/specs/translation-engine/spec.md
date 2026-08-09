## MODIFIED Requirements

### Requirement: Tradução em lotes
O sistema SHALL agrupar blocos conforme os limites declarados pelo provider, usando tokens para LLMs e caracteres/itens para providers de tradução automática, e SHALL respeitar a concorrência efetiva do provider selecionado. Quando o provider não declarar limite próprio de tamanho de lote, o sistema SHALL usar o limite padrão de 3000 tokens de entrada por lote.

#### Scenario: Livro longo
- **WHEN** um livro possui muitos capítulos
- **THEN** a tradução acontece em lotes paralelos, com progresso mensurável por bloco

#### Scenario: Lote limitado por caracteres
- **WHEN** um provider comum declara limite de caracteres menor que o lote atual
- **THEN** o motor divide os blocos antes da requisição sem cortar conteúdo protegido

#### Scenario: Lote padrão ajustado
- **WHEN** um provider LLM não declara limite próprio de lote
- **THEN** os lotes usam o limite padrão de 3000 tokens de entrada, mantendo a saída esperada dentro do teto de saída típico dos modelos

## ADDED Requirements

### Requirement: Passadas iniciais em paralelo
Quando o provider suportar tanto glossário quanto priming, o sistema SHALL executar as duas passadas de preparação em paralelo, de modo que o tempo até o início da tradução seja limitado pela passada mais lenta, não pela soma das duas. Quando apenas uma delas for suportada, a execução SHALL permanecer sequencial e funcional.

#### Scenario: Provider LLM com ambas as passadas
- **WHEN** o usuário inicia uma tradução com um provider LLM que suporta glossário e priming e não há glossário salvo
- **THEN** as duas passadas executam simultaneamente e a tradução começa quando a mais lenta termina

#### Scenario: Provider com uma passada apenas
- **WHEN** o provider suporta apenas glossário ou apenas priming
- **THEN** a passada suportada executa normalmente e a outra é omitida, sem erro

#### Scenario: Glossário já salvo
- **WHEN** já existe glossário salvo para o livro
- **THEN** apenas a passada de priming é necessária e a passada de glossário não é reexecutada
