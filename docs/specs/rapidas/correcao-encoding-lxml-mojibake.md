# Modificação Rápida: Correção de encoding no parsing XHTML (lxml), sanitização de mojibake e rotação de logs

*(preenchido em conjunto por desenvolvedor e IA — sem debate de trade-offs, sem ADR)*

## O que muda
1. Forçar explicitamente a decodificação UTF-8 (`lxml.html.HTMLParser(encoding="utf-8")` ou `source.decode("utf-8")`) em todos os pontos de parsing XHTML com `lxml` (`segments.py`, `index_rebuilder.py`, `toc.py`), evitando que arquivos sem `<meta charset="utf-8">` ou declaração XML sejam interpretados por padrão como ISO-8859-1 (Latin-1).
2. Expandir `_MOJIBAKE_MAP` em `quality.py` com substituições defensivas para sequências conhecidas de double-encoding de 3 bytes (aspas inglesas curvas `“ ”`, travessões `– —`, apóstrofo `’`, marcadores `•`, reticências `…`) e espaços não-quebráveis (`Â\xa0` $\to$ `\xa0`).
3. Ajustar a seleção de arquivos em `book.py` para verificar se o nó selecionado é um arquivo `.epub` antes de chamar `open_ebook()`, evitando falso-positivos de `NotEpubError`/`DrmError` em `erros.log` ao navegar por pastas.
4. Implementar rotação automática de logs em `dump_error_details` (`src/tradutor/tui/errors.py`), limitando o tamanho de `erros.log` (ex: máx. 2 MB com até 3 arquivos de backup rotacionados) para evitar crescimento indefinido.

## Por que
- O parser `lxml.html.document_fromstring(source)` ao receber `bytes` sem declaração explícita de charset assume Latin-1, corrompendo sequências multibyte UTF-8 válidas (gerou 2.560 ocorrências de `Â\xa0` e 635 pontuações corrompidas no `ddd-pt-BR.epub`).
- O arquivo `erros.log` atinge centenas de kilobytes e milhares de linhas por falta de rotação e por registrar cliques em diretórios durante a navegação na árvore de arquivos.

## Arquivos afetados
- `src/tradutor/epub/segments.py` — configurar parser com `encoding="utf-8"` em `parse_chapter` e `render_chapter`.
- `src/tradutor/epub/index_rebuilder.py` — configurar parser com `encoding="utf-8"` nas funções de leitura e reconstrução do índice.
- `src/tradutor/epub/toc.py` — configurar parser com `encoding="utf-8"` na extração/atualização do sumário visual.
- `src/tradutor/domain/quality.py` — incluir mapeamento de mojibake de pontuação de 3 bytes e `Â\xa0` em `_MOJIBAKE_MAP`.
- `src/tradutor/tui/screens/book.py` — checar se o caminho selecionado é arquivo `.epub` antes de despachar o worker de abertura.
- `src/tradutor/tui/errors.py` — implementar rotação de arquivo ao gravar em `erros.log`.
- `tests/epub/test_encoding_regression.py` — novos testes de regressão de parsing/serialização com caracteres UTF-8 e recuos `&nbsp;`.
- `tests/tui/test_errors.py` — teste de rotação de log ao atingir o limite de tamanho.

## Risco de Regressão
Baixo — a alteração apenas assegura que o conteúdo original em UTF-8 seja preservado com fidelidade durante a extração e a reconstituição dos blocos, que cliques em pastas não disparem erro e que o arquivo de log seja rotacionado sem perder histórico recente.

## Precisa de teste novo?
Sim:
- Teste unitário de parsing/renderização de XHTML contendo `&nbsp;`, `\xc2\xa0`, aspas `“ ”` e travessão `—` sem tag `<meta charset>`, garantindo ausência de `Â\xa0` e de bytes `0x80-0x9F` na saída.
- Teste unitário de `fix_mojibake` cobrindo aspas curvas, travessões e `Â\xa0`.
- Teste de TUI verificando que clique em diretórios na árvore não gera log de erro.
- Teste de rotação de `erros.log` ao ultrapassar o limite de tamanho.

---

## ⚠️ Trava de Escalonamento

- Introduz um Ator/papel de usuário novo? **não**
- Cria ou muda uma regra de acoplamento entre componentes já registrada no `arquitetura.html`? **não**
- Contraria ou exige revisar um ADR aprovado? **não**
- Muda comportamento observável de forma que mereça uma decisão arquitetural registrada? **não**
