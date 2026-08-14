# Especificação da Funcionalidade: Fidelidade Estrutural Avançada, Sanitização e Reordenação Semântica de Índices EPUB

---

## 1. Entrada do Desenvolvedor: Mapeamento de Atores & Ações
*(fornecido pelo desenvolvedor e validado na Etapa 1)*

### Contexto / Objetivo Resumido
Garantir fidelidade visual e estrutural absoluta na tradução de e-books EPUB para qualquer idioma de destino — protegendo deterministicamente mídia inline e âncoras posicionais, higienizando caracteres contra *mojibake*, herdando estilos CSS em documentos sintéticos e reconstruindo índices remissivos com ordenação alfabética natural e multilíngue.

### Papéis de Usuário Envolvidos
- **Leitor (Usuário Final):** Usuário que consome o e-book traduzido em leitores digitais (Kindle, Kobo, Thorium, Calibre, etc.).

### Ator: Leitor (Usuário Final)
- **US-01:** Como leitor, quero abrir o EPUB traduzido e ver todas as imagens originais (folha de rosto, figuras, ilustrações inline e logos) exatamente nas posições corretas.
- **US-02:** Como leitor, quero clicar em links de números de página, referências cruzadas e notas de rodapé sem me deparar com âncoras ou links quebrados.
- **US-03:** Como leitor, quero ler o texto sem artefatos visuais de codificação de caracteres (*mojibake* como `Â `, `â€“` ou `faÃ§ade`).
- **US-04:** Como leitor, quero consultar o índice remissivo ao final do livro perfeitamente reordenado de A a Z de acordo com o idioma de destino selecionado na tradução (ex.: `pt-BR`, `es`, `fr`, `de`), e não preso à ordenação alfabética do inglês.
- **US-05:** Como leitor, quero que o apêndice de glossário gerado herde a mesma identidade visual, tipografia e margens dos demais capítulos do livro.

### Ator: Desenvolvedor (Mantenedor)
- **DEV-01:** Como desenvolvedor, quero que a solução seja puramente modular, mantendo o domínio livre de dependências de I/O e a camada `epub` responsável pela manipulação de XHTML/OPF.
- **DEV-02:** Como desenvolvedor, quero uma suíte abrangente de testes automatizados com cobertura `>= 95%`, cobrindo fixtures de índices complexos, imagens inline, classes CSS de código e caracteres tipográficos especiais.
- **DEV-03:** Como desenvolvedor, quero que todo o código passe nas validações de qualidade e estilo (`hatch run lint`, `hatch run fmt-check`, `hatch run cov`).

### Ator: Sistema (Automações / Background)
- **SYS-01:** O sistema deve isolar tags de mídia (`img`, `picture`, `hr`) e âncoras posicionais vazias (`<a id="...">`, `<span id="...">`) como placeholders determinísticos `{{N}}` antes de enviar blocos para tradução.
- **SYS-02:** O sistema deve reconhecer elementos com classes CSS semânticas de código (`programlisting`, `code`, `sourcecode`, etc.) e tratá-los como blocos protegidos.
- **SYS-03:** O sistema deve sanitizar sequências UTF-8 antes do envio e aplicar filtro anti-*mojibake* na recepção das respostas dos provedores.
- **SYS-04:** O sistema deve detectar documentos de índice remissivo, extrair sua árvore de termos, traduzir os termos, reclassificá-los alfabeticamente segundo o idioma de destino (`target_lang`) e reconstruir a árvore XHTML preservando os links de páginas intactos.
- **SYS-05:** O sistema deve descobrir folhas de estilo CSS no OPF do livro e injetar as referências `<link rel="stylesheet">` nos documentos sintéticos gerados (apêndice de glossário).

---

## 2. Análise Arquitetônica & Trade-offs
*(preenchido pela IA com base em Richards & Ford)*

### Características Arquitetônicas Críticas (-ilities)
- **Corretude / Fidelidade Estrutural (Correctness & Fidelity):** Nenhuma marcação HTML, âncora posicional ou imagem pode ser perdida ou corrompida durante a tradução. A restauração de placeholders é garantida por contrato formal (`is_faithful`).
- **Modularidade & Coesão (Modularity):** A lógica de reconstrução de índices e manipulação de XHTML reside exclusivamente na camada `epub`, enquanto a sanitização de texto e regras declarativas de proteção residem na camada `domain`.
- **Internacionalização & Flexibilidade (i18n & Collation):** A reordenação de índices e higienização textual suporta qualquer idioma de destino configurado pelo usuário, utilizando regras de colação Unicode agnósticas de locale fixo.
- **Resiliência (Robustness):** Filtro anti-*mojibake* tolerante a falhas de tokenizers de LLMs, garantindo persistência limpa no cache `estado.json`.

### Trade-offs Aceitos
> **Decisão de Trade-off:** Reconstrução Estruturada de Índices vs. Desempenho de Parsing.
> - *Sacrifício:* O processamento de arquivos de índice remissivo requer um passo adicional de decomposição da árvore de termos e reordenação com colação Unicode antes da serialização final.
> - *Ganho:* Entrega um índice remissivo utilizável e profissional em qualquer idioma de destino, eliminando o defeito grave de índices traduzidos que mantinham a ordem alfabética do inglês.

---

## 3. Estrutura Física & Módulos

### Mapeamento no Projeto Existente
```text
src/tradutor/
├── domain/
│   ├── protection.py                <-- [MODIFICADO: ampliação da política de tags e classes]
│   ├── placeholders.py              <-- [MODIFICADO: suporte a âncoras vazias e validação]
│   └── quality.py                   <-- [MODIFICADO: filtro sanitizador anti-mojibake]
├── epub/
│   ├── appendix.py                  <-- [MODIFICADO: injeção de stylesheets descobertas no OPF]
│   ├── container.py                 <-- [MODIFICADO: exposição da lista de stylesheets do livro]
│   ├── segments.py                  <-- [MODIFICADO: proteção inline de mídia e âncoras vazias]
│   ├── writer.py                    <-- [MODIFICADO: integração de stylesheets e índices]
│   └── index_rebuilder.py           <-- [NOVO MÓDULO: parser, tradução e reordenação de índices]
└── translate/
    ├── pipeline.py                  <-- [MODIFICADO: aplicação de sanitização de strings na saída]
    └── orchestrator.py              <-- [MODIFICADO: suporte à orquestração de reconstrução de índices]
```

### Regras de Acoplamento & Limites
- **`domain`:** Continua com **zero dependências externas e zero I/O**. Funções puras de identificação de regras (`protection.py`), placeholders (`placeholders.py`) e sanitização de texto (`quality.py`).
- **`epub/index_rebuilder.py`:** Depende apenas de `lxml.html`, `domain` (modelos de blocos/termos) e `unicodedata`. Não faz chamadas de rede nem acessa diretamente provedores de LLM.
- **`epub/appendix.py`:** Recebe lista de caminhos de CSS da camada de orquestração/container e injeta no cabeçalho do documento gerado.

---

## 4. Fluxo de Execução & Casos de Borda

### Sequência Lógica

1. **[Extração e Segmentação]:**
   - Ao ler cada capítulo XHTML, `segments.py` consulta `is_protected()` e identifica:
     - Tags de mídia inline (`img`, `picture`, `hr`);
     - Elementos com classes de código (`programlisting`, `code`, etc.);
     - Âncoras posicionais vazias (`<a id="...">` ou `<span id="...">` sem texto interno).
   - Todos esses elementos são substituídos por placeholders `{{0}}`, `{{1}}`, ... preservando seu conteúdo original intacto em `ExtractedText.protected`.

2. **[Detecção de Índice Remissivo]:**
   - `index_rebuilder.py` inspeciona o documento. Se for identificado como índice remissivo (via metadados OPF `type="index"` ou cabeçalhos de letra com listas de links de páginas), seus termos são extraídos como blocos vinculados à árvore hierárquica (`IndexTerm`).

3. **[Tradução e Sanitização]:**
   - Os blocos são enviados em lotes ao provedor.
   - Antes do envio, strings passam por normalização NFC e proteção de espaços `\xa0`.
   - Na resposta, `pipeline.py` aplica o filtro anti-*mojibake* para garantir caracteres acentuados, aspas e travessões limpos em UTF-8.

4. **[Reconstrução e Reordenação Multilíngue]:**
   - Capítulos normais: restauram placeholders `{{N}}` (incluindo imagens e âncoras) e gravam no documento.
   - Arquivo de índice remissivo: `index_rebuilder.py` reordena os termos alfabeticamente conforme o `target_lang` (removendo diacríticos da chave de ordenação para agrupamento correto), recalcula as letras mestras (A–Z) e remonta o XHTML com os links originais preservados.

5. **[Montagem do EPUB de Saída]:**
   - `writer.py` consulta o `container` para obter as folhas de estilo (`.css`) e passa a lista para `build_appendix_xhtml`, que inclui as tags `<link rel="stylesheet">` no `<head>` do apêndice de glossário.

### Casos de Borda e Erros

- **Índice sem Cabeçalhos de Letra:** Se o índice original for uma lista plana sem seções `<p class="indexletter">`, o reconstrutor detecta o padrão e gera automaticamente os agrupadores alfabéticos conforme a língua de destino.
- **Termos com Caracteres Especiais / Numéricos:** Termos que iniciam com dígitos ou símbolos (ex.: *3-Tier Architecture*, *.NET*) são agrupados em uma seção inicial dedicada (ex.: `0-9` ou `#`).
- **Idiomas com Alfabetos Especiais:** A chave de ordenação utiliza `unicodedata.normalize('NFD', ...)` e colação flexível, permitindo ordenação natural em português, espanhol, francês, alemão, etc.
- **Imagens em Múltiplos Formatos:** Suporte a tags `<img>` autocontidas (`<img .../>`) e abertas (`<img ...></img>`), além de `<figure>` e `<picture>`.
- **E-books sem Folhas de Estilo CSS:** Se o EPUB original não possuir nenhum arquivo `.css` no manifesto, o apêndice de glossário utiliza estilos limpos de fallback sem gerar links quebrados.

---

## 5. Proposta de ADR — Registro de Decisão Arquitetônica

- **Título:** ADR-06: Preservação Estrutural Determinística e Reconstrução Semântica Multilíngue de Índices EPUB
- **Contexto:** Durante auditoria comparativa de e-books traduzidos, constatou-se que tags inline não-textuais (`<img>`), âncoras de numeração de páginas (`<a id="...">`) e classes de código CSS (`programlisting`) eram suscetíveis a descarte ou corrupção por LLMs quando não protegidas por placeholders. Além disso, índices remissivos traduzidos mantinham a ordem alfabética do idioma original em inglês, e documentos gerados dinamicamente (glossário) perdiam o CSS do livro.
- **Decisão:** 
  1. Estender a política de proteção determinística para incluir mídia, classes semânticas de código e âncoras posicionais vazias.
  2. Implementar módulo dedicado `epub/index_rebuilder.py` para parsear, traduzir, reordenar por colação do idioma de destino e reconstruir índices remissivos.
  3. Adicionar camada de sanitização e filtro anti-*mojibake* na saída do pipeline de tradução.
  4. Descobrir e injetar automaticamente as folhas de estilo do livro em qualquer documento sintético gerado.
- **Consequências:**
  - *Positivas:* 100% de imagens preservadas; 0 links quebrados de páginas/notas; índice remissivo legível e perfeitamente ordenado em qualquer idioma; eliminação de caracteres corrompidos (`Â `, `â€“`); identidade visual homogênea no apêndice.
  - *Negativas:* Pequena complexidade adicional no módulo `epub` para manipulação de árvores de índice.

---

## 6. Funções de Aptidão (Fitness Functions) & Critérios de Aceite

- [x] **Preservação de Mídia:** Nenhuma tag `<img>` existente no original é perdida após a tradução de capítulos com imagens inline.
- [x] **Integridade de Âncoras e Links:** 100% das âncoras vazias (`<a id="...">`, `<span id="...">`) são preservadas, resultando em 0 links quebrados no EPUB de saída.
- [x] **Reordenação do Índice em PT-BR / Idioma Alvo:** As entradas do índice remissivo traduzido estão estritamente em ordem alfabética de A a Z de acordo com os termos no idioma de destino.
- [x] **Ausência de Mojibake:** Zero ocorrências de sequências de *double-encoding* (`Â `, `â€“`, `â€œ`, `faÃ§ade`) no cache `estado.json` e nos arquivos XHTML traduzidos.
- [x] **Herança de CSS no Apêndice:** O arquivo `apendice-glossario.xhtml` contém `<link rel="stylesheet">` apontando para os mesmos arquivos CSS do livro original presentes no manifesto OPF.
- [x] **Cobertura de Testes:** Suíte de testes unitários e de integração com cobertura total `>= 95%`.
- [x] **Linter e Formatação:** `hatch run lint` e `hatch run fmt-check` 100% verdes sem avisos.

---

## 7. Reconciliação Pós-Implementação

- **Data da Reconciliação:** 14/08/2026
- **Status:** Implementado Conforme Especificado
- **Observações:**
  - Todas as 5 histórias de usuário (US-01 a US-05) e as ações do sistema (SYS-01 a SYS-05) foram atendidas fielmente.
  - A cobertura global de testes atingiu 95.0% com 643 testes aprovados.
  - O painel de arquitetura (`docs/arquitetura/arquitetura.html`) e as especificações principais do OpenSpec foram atualizados e sincronizados.

