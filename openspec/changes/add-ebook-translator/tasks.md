# Tasks — Add Ebook Translator (v1)

## 1. Setup do projeto

- [x] 1.1 Inicializar projeto hatch com layout `src/tradutor/` + `tests/` + `pyproject.toml` (Python 3.12+, entry point `tradutor`)
- [x] 1.2 Adicionar dependências de runtime (textual, lxml, ebooklib, httpx, tiktoken, keyring, platformdirs, cryptography, pydantic) e dev (pytest, coverage, hypothesis, respx, ruff)
- [x] 1.3 Adicionar `LICENSE` AGPL-3.0, `README.md` (pt-BR) e `.gitignore` (ignorando configs/caches/chaves)
- [x] 1.4 Criar `config.example.toml` com todas as seções documentadas
- [x] 1.5 Configurar ruff (lint+format) e pipeline pytest+coverage com gate global ≥95%
- [x] 1.6 Criar workflow GitHub Actions: lint + testes + cobertura

## 2. Domínio: blocos e proteção (funções puras, 100% branch)

- [x] 2.1 Modelo `Block` (id, kind, text, protected) e `Chapter` (lista de blocos + metadados)
- [x] 2.2 Política de proteção declarativa: seletores para `code`/`pre`/`svg`/`math`/`script`/`style`
- [x] 2.3 Mecânica de placeholders `{{N}}`: extração de conteúdo protegido e substituição de volta
- [x] 2.4 Verificador de fidelidade de placeholders (detecta resposta corrompida)
- [x] 2.5 Testes de propriedade (hypothesis): segmentação idempotente em XHTML arbitrário
- [x] 2.6 Garantir 100% de cobertura branch nos módulos do domínio

## 3. EPUB: leitura e escrita cirúrgica

- [x] 3.1 Leitor de container ZIP: `mimetype` obrigatório, manifest/OPF, spine, EPUBS 2 e 3
- [x] 3.2 Parsing de capítulos com lxml e caminhada de nós de texto → blocos
- [x] 3.3 Escritor in-place: rezip preservando nomes/ordem/compressão, `mimetype` primeiro e `stored`
- [x] 3.4 Atualização de metadados: `dc:language`, `dc:date` (modificado), `dc:title` traduzido; manifest/spine intactos
- [x] 3.5 Tradução dos rótulos do sumário (nav.xhtml e toc.ncx) mantendo links
- [x] 3.6 Detecção de DRM com erro claro
- [x] 3.7 Modo reparo via ebooklib para EPUBs mal formados (aviso ao usuário)
- [x] 3.8 Fixtures douradas: livros miniatura EPUB 2 e EPUB 3 + testes de byte-diff (intocados idênticos; tocados diferem só no texto)
- [x] 3.9 Cobertura ≥95% no módulo epub

## 4. Providers

- [x] 4.1 Porta `Translator`: `translate(batch, context) -> TranslationBatch{texts, usage}`
- [x] 4.2 `PromptContext` (idiomas, política, glossário, priming) montado pelo núcleo
- [x] 4.3 Adapter `OpenAICompatProvider` com `base_url`/`model` configuráveis (default DeepSeek)
- [x] 4.4 Retry: backoff exponencial com jitter, `Retry-After`, 429/5xx/timeout transitórios, 4xx definitivos
- [x] 4.5 Exposição de `usage` (tokens in/out) por resposta
- [x] 4.6 Teste de conexão (endpoint de modelos) com mensagens claras
- [x] 4.7 Testes com API falsa (respx): sucesso, 429, timeout, resposta quebrada, usage; falha definitiva não interrompe o livro

## 5. Passadas de qualidade

- [x] 5.1 Passada de glossário: amostra de capítulos → lista de termos/nomes próprios → `glossario.json`
- [x] 5.2 Passada de priming: resumo de estilo/tom do livro
- [x] 5.3 Política de termos técnicos (traduzir/manter/híbrido) aplicada no prompt e validada
- [x] 5.4 Versão do glossário: edições manuais do JSON mudam a versão e invalidam o cache
- [x] 5.5 Geração do apêndice de glossário (original → tradução) no backmatter do livro de saída
- [x] 5.6 Testes com provider fake: glossário aplicado consistentemente, política híbrida, saída limpa (sem marcas de IA)

## 6. Orquestração, cache e paralelismo

- [x] 6.1 Diretório de trabalho por livro (`estado.json` + `glossario.json`) com escrita atômica
- [x] 6.2 Chave de compatibilidade do estado: hash(livro + source + target + modelo + política + versão glossário)
- [x] 6.3 Agrupamento de blocos em lotes respeitando limites de contexto
- [x] 6.4 Paralelismo configurável (default 4) com fila por lote
- [x] 6.5 Retomada: interrupção/cancelamento preserva progresso e retoma sem re-traduzir
- [x] 6.6 Leitura tolerante de `estado.json` corrompido (re-traduz blocos afetados)
- [x] 6.7 Testes: retomada após falha de rede, cancelamento, mudança de modelo/idioma invalida estado, cache corrompido

## 7. Custo

- [x] 7.1 Contagem de tokens pré-voo com tiktoken (cl100k_base) sobre blocos traduzíveis (protegidos excluídos)
- [x] 7.2 Tabela de fatores de expansão por idioma alvo
- [x] 7.3 Estimativa: tokens in/out, custo US$, tempo (lotes × latência / paralelismo)
- [x] 7.4 Tabela de preços editável no config (entrada/saída por milhão)
- [x] 7.5 Teto de gasto: checagem após cada lote contra uso acumulado; aborta com aviso
- [x] 7.6 Relatório final real-vs-previsto (usage exato da API)
- [x] 7.7 Testes: estimativa ignora blocos protegidos, teto dispara e preserva cache, preços editados refletem na estimativa

## 8. Infra: configuração, segredos e logs

- [x] 8.1 Schema pydantic do config (provider, providers, translation, cost, execution) com defaults sensatos
- [x] 8.2 Carga/validação via `platformdirs.user_config_dir` + tomllib; erros apontam o campo
- [x] 8.3 Porta `SecretStore` com backend keyring (default) e teste com keyring fake
- [x] 8.4 Backend de arquivo cifrado (Fernet + senha-mestra por sessão) e teste
- [x] 8.5 Override por variável de ambiente (`DEEPSEEK_API_KEY`) e precedência env > cofre > arquivo > prompt
- [x] 8.6 Utilitário de redação aplicado em logs/erros/relatórios; teste de que nenhuma saída contém chave
- [x] 8.7 Teste de que o domínio nunca recebe chaves (arquitetura)

## 9. TUI (Textual)

- [x] 9.1 Telas: primeira execução guiada (configuração de chave + teste de conexão)
- [x] 9.2 Tela de configuração: provider, chave mascarada, idiomas, política, paralelismo
- [x] 9.3 Tela de estimativa com resumo do livro, aviso de estimativa, recomendação de limites e confirmação
- [x] 9.4 Tela de progresso: barra por bloco, ETA vivo (vazão medida), logs redigidos, cancelamento ordenado
- [x] 9.5 Tela de relatório final (real-vs-previsto + caminho do arquivo) e oferta de retomada quando cache existir
- [x] 9.6 Mensagens de erro acionáveis em pt-BR (DRM, chave, config, rede, teto)
- [x] 9.7 Testes com `textual.pilot` dos fluxos principais
- [x] 9.8 Substituir a entrada de texto por `DirectoryTree` na tela de seleção de livro para facilitar a navegação do usuário
- [x] 9.9 Adicionar botão 'Subir pasta' na tela de seleção de livro para permitir navegar para diretórios pais e fora do projeto
- [x] 9.10 Configurar identidade visual (título do app) como `LiberLingua` no Header
- [x] 9.11 Definir atalhos globais no Footer (`q` para sair, `c` para config, `h` para ajuda) e remover botões redundantes na `BookScreen`
- [x] 9.12 Criar tela modal de ajuda (`HelpScreen`) acionável via atalho `h` detalhando o funcionamento do app
- [x] 9.13 Traduzir a interface (rótulos, dicas, prompts) para utilizar "Provedor" em vez de "Provider"
- [x] 9.14 Adicionar campos de modelo (dropdown dinâmico `#model-select` e input manual `#model`) na tela de configuração
- [x] 9.15 Associar o estado dos modelos e a seleção de forma isolada ao provedor selecionado na UI
- [x] 9.16 Atualizar o teste de conexão da UI para usar o provedor/modelo selecionados no formulário em vez de ler do disco
- [x] 9.17 Ajustar o teste de conexão para retornar com sucesso em status 404/405/501 (rota de modelos indisponível), disparando o fallback manual na UI
- [x] 9.18 Ajustar o salvamento de configurações na TUI para persistir o modelo selecionado no respectivo provedor no arquivo TOML
- [x] 9.19 Adicionar testes de unidade e de integração na TUI cobrindo a seleção dinâmica de modelos e o fallback manual

## 10. Integração final e qualidade

- [x] 10.1 Teste ponta a ponta com provider fake: EPUB real → tradução completa → saída `*-pt-BR.epub` válida
- [x] 10.2 Validar saída com epubcheck-like local (bem-formado, manifest/spine íntegros)
- [x] 10.3 Rodar suite completa e atingir gates: domínio 100% branch, global ≥95%
- [x] 10.4 Teste manual opcional com chave DeepSeek real (livro pequeno) e relatório de custo
- [x] 10.5 Revisão final: `openspec validate`, README com instruções de instalação (`uv tool`/pipx) e uso
