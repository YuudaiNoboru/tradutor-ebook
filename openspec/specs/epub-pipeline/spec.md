# epub-pipeline Specification

## Purpose

Extrai e reescreve livros EPUB (2 e 3) preservando a formatação original: segmenta o XHTML em blocos de texto traduzíveis e protegidos, e produz um EPUB de saída estruturalmente idêntico ao original.
## Requirements
### Requirement: Leitura de EPUB 2 e EPUB 3
O sistema SHALL ler livros EPUB 2 e EPUB 3, identificando o container ZIP, o manifest (OPF), o spine e a navegação (toc.ncx e/ou nav.xhtml).

#### Scenario: Leitura de livro válido
- **WHEN** o usuário seleciona um EPUB válido (EPUB 2 ou 3)
- **THEN** o sistema extrai os arquivos e identifica os capítulos, o sumário e os metadados sem modificar o arquivo original

### Requirement: Segmentação em blocos de texto
O sistema SHALL converter o XHTML de cada capítulo em uma sequência de blocos de texto, preservando o contexto de formatação de cada bloco (parágrafo, título, tabela, nota de rodapé, etc.).

#### Scenario: Segmentação de capítulo com formatação mista
- **WHEN** um capítulo contém títulos, parágrafos, negritos, itálicos e notas de rodapé
- **THEN** cada unidade de texto é extraída como bloco com seu contexto, e as tags de formatação permanecem associadas ao bloco

### Requirement: Proteção determinística de conteúdo
O sistema SHALL tratar como protegido (nunca enviado para tradução) o conteúdo de: blocos e elementos de código (`code`/`pre` e elementos com classes semânticas de código como `programlisting`), SVG, MathML, `script`, `style`, elementos de mídia inline (`img`, `picture`, `hr`) e âncoras posicionais vazias (`<a id="...">`, `<span id="...">` sem texto interno). Conteúdo protegido SHALL ser substituído por placeholders `{{N}}` que a tradução copia e restaura verbatim.

#### Scenario: Código dentro de capítulo
- **WHEN** um capítulo contém blocos de código entre parágrafos ou formatados com classes CSS de código
- **THEN** os blocos de código não são enviados ao tradutor e retornam ao EPUB final byte a byte idênticos

#### Scenario: Texto dentro de SVG e MathML
- **WHEN** um capítulo contém texto em elementos SVG ou MathML
- **THEN** esse texto não é traduzido e permanece intacto na saída

#### Scenario: Imagens e âncoras inline em parágrafos
- **WHEN** um parágrafo contém tags `<img>` ou âncoras vazias de paginação `<a id="page_xxx"/>`
- **THEN** as tags são convertidas em placeholders `{{N}}` e restauradas em suas posições exatas na saída, garantindo que nenhuma imagem ou âncora seja perdida

### Requirement: Escrita cirúrgica in-place
O sistema SHALL reescrever o EPUB preservando a estrutura interna: arquivos não traduzidos permanecem byte a byte idênticos, arquivos traduzidos diferem somente nos nós de texto traduzidos, a entrada `mimetype` permanece a primeira do ZIP e sem compressão, e a ordem dos arquivos é preservada.

#### Scenario: Livro com capítulos traduzidos e não traduzidos
- **WHEN** a tradução termina e o EPUB de saída é escrito
- **THEN** os arquivos de estilo, imagens e fontes são idênticos ao original, e os capítulos traduzidos diferem apenas no conteúdo de texto

#### Scenario: Preservação da entrada mimetype
- **WHEN** o EPUB de saída é gerado
- **THEN** a entrada `mimetype` é a primeira do ZIP e armazenada sem compressão

### Requirement: Metadados de saída
O sistema SHALL atualizar no EPUB de saída: `dc:language` para o idioma alvo, `dc:date` para a data de modificação e `dc:title` com o título traduzido. Manifest e spine SHALL permanecer intactos.

#### Scenario: Metadados atualizados
- **WHEN** a tradução é concluída com destino pt-BR
- **THEN** o OPF de saída declara `dc:language` pt-BR, data modificada e título traduzido, mantendo o restante dos metadados

### Requirement: Sumário traduzido
O sistema SHALL traduzir os rótulos do sumário (nav.xhtml e toc.ncx) para o idioma alvo, mantendo os destinos dos links intactos.

#### Scenario: Sumário com capítulos em inglês
- **WHEN** um livro tem sumário com capítulos em inglês
- **THEN** o EPUB de saída apresenta os rótulos traduzidos e os links apontando para os mesmos destinos

### Requirement: Detecção de DRM
O sistema SHALL detectar livros protegidos por DRM e abortar a tradução com uma mensagem clara.

#### Scenario: Livro protegido
- **WHEN** o usuário seleciona um EPUB protegido por DRM
- **THEN** a tradução é abortada e a mensagem informa que o livro está protegido

### Requirement: Modo reparo
O sistema SHALL oferecer um modo reparo para EPUBs mal formados, reconstruindo o livro de forma válida, e SHALL avisar o usuário quando a reconstrução for necessária.

#### Scenario: EPUB mal formado
- **WHEN** um EPUB possui estrutura inválida que impede a cirurgia in-place
- **THEN** o sistema propõe o modo reparo, reconstruindo um EPUB válido com os textos traduzidos

### Requirement: Arquivo de saída separado
O sistema SHALL gravar o resultado em um novo arquivo com sufixo do idioma alvo (ex.: `livro-pt-BR.epub`) e SHALL nunca sobrescrever o arquivo original.

#### Scenario: Geração da saída
- **WHEN** a tradução termina
- **THEN** um novo arquivo `livro-pt-BR.epub` é criado ao lado do original, que permanece inalterado

### Requirement: Decodificação e serialização estrita em UTF-8
O sistema SHALL decodificar e serializar todos os arquivos XHTML internos do EPUB estritamente em UTF-8 durante todas as etapas do pipeline (segmentação, reconstrução de índice e sumário), garantindo que arquivos sem declaração explícita de charset no cabeçalho XML ou sem `<meta charset="utf-8">` não sejam interpretados por padrão como ISO-8859-1 (Latin-1).

#### Scenario: XHTML sem declaração explícita de charset
- **WHEN** um capítulo XHTML contém espaços não-quebráveis (`&nbsp;` / `\xc2\xa0`), aspas inglesas curvas (`“ ”`), travessões (`– —`) e não possui declaração explícita de charset
- **THEN** o sistema processa e reescreve o documento preservando os caracteres UTF-8 originais, sem introduzir o caractere `Â` em recuos de código e sem converter pontuações em caracteres de controle da faixa 0x80-0x9F

### Requirement: Herança de estilos em documentos sintéticos
O sistema SHALL descobrir todas as folhas de estilo CSS registradas no manifesto OPF do EPUB original e injetar as tags `<link rel="stylesheet">` correspondentes no cabeçalho `<head>` de documentos sintéticos gerados (como o apêndice de glossário).

#### Scenario: Apêndice de glossário com folhas de estilo do livro
- **WHEN** o apêndice de glossário é gerado para o EPUB de saída
- **THEN** o arquivo XHTML do apêndice referencia as mesmas folhas de estilo CSS utilizadas pelos demais capítulos do livro

### Requirement: Normalização de placeholders em palavras hifenizadas
O sistema SHALL detectar e normalizar sequências de extração onde um placeholder determinístico de elemento protegido ou âncora inline posicional foi inserido no meio de uma palavra com hífen (ex.: `every-{{0}}one`), descolando a âncora/placeholder para após a palavra unificada (ex.: `everyone {{0}}`), garantindo que o vocábulo seja apresentado de forma íntegra ao motor de tradução e o placeholder seja restaurável na reconstrução cirúrgica.

#### Scenario: Âncora no meio de palavra com hífen
- **WHEN** um elemento de texto do EPUB contém uma âncora ou tag inline no meio de uma palavra hifenizada tipograficamente (`palavra-<a id="..."></a>resto`)
- **THEN** a extração produz um template com a palavra unificada e o placeholder posicionado adjacente (`palavraresto {{0}}`), permitindo tradução natural e reinserção correta da âncora no XHTML final
