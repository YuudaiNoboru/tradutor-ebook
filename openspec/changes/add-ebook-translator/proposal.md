# Add Ebook Translator (v1)

## Why

Leitores brasileiros de livros técnicos enfrentam barreira de idioma: a maioria dos títulos está em inglês e a oferta em português é escassa. As soluções existentes não atendem: Immersive Translate não permite escolher qualquer LLM no modo gratuito, e o plugin do Calibre prende o usuário ao ecossistema Calibre. Ambas (e muitas outras) perdem a formatação original do livro (negritos, itálicos, rodapés, títulos). Criar um tradutor de EPUB simples, de terminal, que usa as chaves do próprio usuário (BYOK), preserva a formatação e é aberto (AGPL-3.0).

## What Changes

- **App de terminal (TUI com Textual)**: o usuário seleciona um EPUB, o idioma de destino (default `pt-BR`), o provider e traduz — tudo em telas guiadas em português.
- **Pipeline de tradução**: deszipa o EPUB → segmenta o XHTML em blocos de texto → protege determinísticamente código, SVG, MathML, script e style → traduz via LLM → reescreve o EPUB com **cirurgia in-place** (arquivos intocados ficam byte a byte idênticos; só nós de texto mudam).
- **Qualidade de tradução**: passada de glossário (extrai termos do domínio e nomes próprios; arquivo JSON editável à mão), passada de priming (resumo do estilo do livro), política de termos técnicos (traduzir/manter/híbrido), apêndice de glossário no livro traduzido.
- **Providers plugáveis**: porta `Translator` + adapter OpenAI-compatível (DeepSeek hoje; `base_url` configurável já habilita Ollama/OpenRouter). Porta pronta para Anthropic/Gemini no futuro.
- **Custo e velocidade**: estimativa pré-voo em US$ com aviso explícito de estimativa, teto de gasto configurável (aborta se o uso real estourar), paralelismo configurável, retry com backoff.
- **Cache/retomada**: tradução por bloco com chave `(livro + source + target + modelo + política + versão do glossário)`; interrupções retomam sem re-traduzir.
- **Segurança**: chaves no cofre do SO (keyring/DPAPI/Keychain) com fallback de arquivo cifrado (Fernet + senha por sessão) e override por variável de ambiente; redação total de chaves em logs; chaves nunca atravessam o núcleo do domínio.
- **Saída**: apenas traduzido, com `dc:title`, TOC/NCX e `dc:language` atualizados; arquivo de saída `*-pt-BR.epub` (original nunca é sobrescrito); modo reparo (ebooklib) para EPUBs mal formados.
- **Testes com cobertura máxima**: domínio 100% (branch coverage), adapters com API falsa, testes dourados de EPUB (diff byte a byte), gate global ≥95% no CI.
- **Licença AGPL-3.0** (radical: o projeto permanece aberto em qualquer derivação, inclusive SaaS).

## Capabilities

### New Capabilities

- `epub-pipeline`: leitura de EPUB 2/3 (zip + XHTML), segmentação em blocos, política de proteção (code/pre/SVG/MathML/script/style), escrita cirúrgica in-place preservando estrutura, modo reparo para EPUBs mal formados, detecção de DRM.
- `llm-provider`: porta `Translator`, adapter OpenAI-compatível (DeepSeek), configuração de `base_url`/modelo, retry com backoff, exposição de `usage` (tokens reais), teste de conexão.
- `translation-engine`: passada de glossário, passada de priming, chunking/batching, paralelismo, política de termos técnicos, apêndice de glossário, saída só-traduzido.
- `translation-cache`: cache por bloco com chave de invalidação completa, retomada de traduções interrompidas.
- `cost-control`: estimativa pré-voo (tokens, US$, tempo), aviso de estimativa, teto de gasto, relatório real-vs-previsto ao final.
- `secret-management`: armazenamento em cofre do SO, fallback de arquivo cifrado, override por variável de ambiente, redação de segredos em logs e erros.
- `configuration`: arquivo `config.toml` em dirs de config por plataforma (`platformdirs`), schema com providers/idiomas/política/tabela de preços/teto/paralelismo, `config.example.toml`.
- `tui-app`: fluxos Textual em pt-BR — primeira execução, configuração de chave, tela de estimativa, barra de progresso com ETA vivo, relatório final, cancelamento e retomada.

### Modified Capabilities

Nenhuma (projeto novo, sem specs existentes).

## Impact

- **Novo repositório** (este diretório): layout `src/tradutor/` gerenciado por hatch; módulos `domain/`, `epub/`, `translate/`, `providers/`, `tui/`, `infra/`.
- **Dependências principais**: textual, lxml, ebooklib (somente modo reparo), httpx, tiktoken, keyring, platformdirs, cryptography; testes: pytest, coverage, hypothesis, respx.
- **CI**: GitHub Actions (lint + testes + gate de cobertura). Distribuição .exe/.app/AppImage é fase 2, fora do escopo desta change.
- **Fora de escopo (v1)**: PDF/mobi/txt/srt, modo lote, bilíngue, OCR de capa, GUI/web, tela de edição de glossário (arquivo manual), tradução de `dc:description`/publisher.
