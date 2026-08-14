# index-rebuilder Specification

## Purpose

Detecta, traduz e reconstrói índices remissivos de e-books EPUB, reordenando termos e subtermos alfabeticamente conforme a língua de destino e preservando todas as âncoras de destino.

## Requirements

### Requirement: Detecção e extração de índice remissivo
O sistema SHALL detectar seções e arquivos de índice remissivo em EPUBs (via metadados OPF, atributo `properties="index"`, guia de landmarks ou padrões estruturais de cabeçalhos de letras e listas de referências a páginas) e extrair os termos para tradução mantendo o vínculo com os links originais.

#### Scenario: Detecção de arquivo de índice
- **WHEN** um EPUB contém um arquivo de índice remissivo (`index.html`) com termos e links de páginas
- **THEN** o sistema identifica a estrutura como índice e extrai os termos principais e subtermos para tradução preservando as referências cruzadas

### Requirement: Reordenação alfabética multilíngue
O sistema SHALL reordenar os termos traduzidos do índice remissivo alfabeticamente conforme as regras de colação do idioma de destino configurado (`target_lang`), ignorando diacríticos/acentuação na ordenação primária e recalculando os agrupamentos por letra (A a Z).

#### Scenario: Termo muda de letra inicial na tradução
- **WHEN** o termo original em inglês "Bounded Context" (letra B) é traduzido para o português "Contexto Delimitado" (letra C)
- **THEN** o termo é movido para a seção da letra C e ordenado alfabeticamente entre os demais termos da letra C

#### Scenario: Tradução para outros idiomas
- **WHEN** o usuário seleciona outro idioma de destino (ex.: espanhol ou francês)
- **THEN** o índice é ordenado segundo a colação natural daquele idioma

### Requirement: Reconstrução fiel do XHTML do índice
O sistema SHALL remontar a árvore XHTML do índice remissivo com os termos traduzidos e reordenados, preservando as classes de estilo originais, identificadores de âncoras locais e links funcionais para os capítulos e páginas de destino.

#### Scenario: Links de páginas e termos subordinados
- **WHEN** o índice traduzido é escrito no EPUB final
- **THEN** todos os links para páginas do livro permanecem clicáveis e direcionam para os mesmos destinos exatos do livro original
