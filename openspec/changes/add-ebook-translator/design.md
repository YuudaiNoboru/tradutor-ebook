# Design — Add Ebook Translator (v1)

## Context

Projeto greenfield (diretório vazio). Ver `proposal.md` para motivação. Restrições que moldam o design: autor é programador hobby (simplicidade e legibilidade importam), AGPL-3.0, BYOK, multiplataforma (Windows/macOS/Linux), v1 é TUI, apenas EPUB, saída só-traduzido com preservação de formatação byte a byte, custo controlado em US$.

## Goals / Non-Goals

**Goals:**
- Núcleo do domínio puro e testável (100% de cobertura branch), independente de TUI, providers e I/O.
- Preservação de formatação *garantida por máquina* (testes dourados de byte-diff), não por confiança na LLM.
- Adicionar um provider novo no futuro = um arquivo de adapter, sem tocar no núcleo.
- Economia de tokens estrutural: código nunca enviado, batches grandes, cache, sem re-tradução.
- Segurança de chaves criptografadas com zero fricção no Windows/macOS.

**Non-Goals:**
- Empacotamento/distribuição (.exe/.app/AppImage) — fase 2 (PyInstaller + GitHub Actions).
- Bilíngue, modo lote, PDF/mobi, OCR, GUI/web — ver `proposal.md` (fora da v1).
- Infraestrutura de servidor, contas, telemetria — app 100% local.

## Decisions

### D1. Arquitetura hexagonal com módulos enxutos (não DDD completo)
Camadas: `domain/` (regras puras), `epub/` (leitura/escrita), `translate/` (orquestração), `providers/` (adapters), `infra/` (config, segredos, cache, redação), `tui/` (driver Textual). A regra de dependência: núcleo não importa adapters; adapters implementam portas definidas no núcleo.

```
┌─────────────────────────────────────────────────────┐
│ tui/  (Textual — driver, só envia comandos/recebe)  │
├─────────────────────────────────────────────────────┤
│ translate/  (orquestração: passadas, lotes, cache)  │
│ domain/     (blocos, proteção, custo — funções puras)│
├─────────────────────────────────────────────────────┤
│ epub/  │ providers/  │ infra/   (adapters e I/O)    │
└─────────────────────────────────────────────────────┘
```
- *Alternativa considerada*: DDD completo com agregados/eventos — rejeitado: complexidade desproporcional para um app de 1 usuário por execução.
- *Alternativa considerada*: tudo em um módulo — rejeitado: mataria a testabilidade exigida.

### D2. EPUB: cirurgia in-place com `zipfile` + `lxml`; ebooklib só no modo reparo
- Ler o EPUB como ZIP (`zipfile`), parsear XHTML com `lxml.html` (tolerante, XHTML/HTML), **caminhar os nós de texto** e substituí-los pelas traduções; reescrever o ZIP preservando nomes, ordem e compressão dos entries, com `mimetype` sempre primeiro e `stored`.
- ebooklib (AGPL, decisão do autor) é usado **apenas** como escape hatch de reconstrução quando a fonte é inválida (modo reparo) — nunca no caminho feliz, para não perder elementos exóticos.
- Fidelidade: testes dourados fazem byte-diff; arquivos intocados idênticos, tocados diferem só no texto.
- *Alternativa considerada*: ebooklib no caminho feliz — rejeitado por risco de reescrever estrutura (é o defeito dos tradutores que o usuário odiou).

### D3. Modelo de blocos com proteção determinística
- `Block = {id, kind (p/ titulo|paragrafo|tabela|...), text, protected: bool}`. Cada capítulo vira uma lista de blocos; conteúdo protegido (`code`, `pre`, `svg`, `math`, `script`, `style`) é **extraído** e substituído por placeholders `{{N}}` que a tradução deve reproduzir verbatim; verificação pós-lote rejeita (retry) respostas que alterem placeholders.
- Regras de proteção = lista declarativa de seletores, expansível.
- *Por que extrair em vez de pedir à LLM para não traduzir*: decisão determinística > probabilística. É o mesmo princípio do Immersive Translate e do plugin Calibre.

### D4. Porta `Translator` + adapter OpenAI-compatível
- Porta: `translate(batch: list[Block], context: PromptContext) -> TranslationBatch{texts, usage}`.
- Adapter único na v1 (`OpenAICompatProvider`) com `base_url` + `model` configuráveis e default DeepSeek — o mesmo protocolo cobre OpenAI, Ollama, Groq, OpenRouter.
- Retry: backoff exponencial com jitter, respeitando `Retry-After` quando presente; 429/5xx/timeout = transitório; 4xx = definitivo (exceto 429).
- `usage` (tokens in/out) vem de cada resposta e alimenta custo real e teto de gasto.

### D5. Qualidade em duas passadas + política de termos
- **Passada glossário**: amostra (primeiros ~10 capítulos) → o modelo lista termos técnicos/nomes próprios → glossário JSON persistido no diretório de trabalho do livro (editável à mão; mudanças alteram a "versão do glossário" da chave de cache).
- **Passada priming**: resumo de estilo/tom do livro → prompt de sistema de todos os lotes.
- **Política de termos**: `traduzir | manter | hibrido` (default híbrido: primeira ocorrência com original em parênteses).
- Apêndice de glossário gerado a partir do mesmo JSON (capítulo final no backmatter).

### D6. Cache/retomada: um arquivo de estado JSON por trabalho
- Cada livro em tradução tem um diretório de trabalho: `estado.json` (blocos, status, traduções, usage acumulado) + `glossario.json`.
- Chave de compatibilidade do estado: hash(conteúdo do livro + source + target + modelo + política + versão do glossário). Divergência → recomeço limpo.
- Escrita atômica (tmp + rename) a cada lote concluído; leitura tolerante (arquivo corrompido → blocos afetados re-traduzidos).
- *Alternativas consideradas*: SQLite (mais robusto, menos inspecionável) e um JSON por bloco (fragmentado) — rejeitadas: JSON único é simples, inspecionável e suficiente.

### D7. Custo: estimativa aproximada + contagem exata
- Pré-voo: `tiktoken` (cl100k_base, aproximação para DeepSeek) sobre o payload real de blocos traduzíveis; fator de expansão por idioma alvo (pt-BR ~1.2; CJK comprime); tabela de preços editável no config; tempo = lotes × latência / paralelismo.
- Pós-voo: usage real somado das respostas (exato). Relatório real-vs-previsto.
- Teto de gasto: após cada lote, se `custo_acumulado > teto` → aborta com aviso; progresso preservado no cache.
- Aviso permanente na tela: "estimativa" + recomendação de limites na conta do provider.

### D8. Segredos: porta `SecretStore` com 3 backends
- `keyring` (Credential Manager/Keychain/libsecret) = default; fallback Fernet (`cryptography`) com senha-mestra por sessão; override por variável de ambiente na convenção do provider (`DEEPSEEK_API_KEY`).
- Precedência: env > cofre > arquivo cifrado > prompt na TUI.
- Redação: utilitário `redact()` aplicado em toda saída de log/erro/report; testes garantem que nenhuma saída contém padrão de chave.
- A chave só existe na camada de adapter; o núcleo vê apenas a porta.

### D9. Configuração: TOML + pydantic
- `tomllib` para ler, **pydantic** para o schema e validação (erros claros com campo/nome, defaults sensatos). Arquivo em `platformdirs.user_config_dir("tradutor-ebook")`; `config.example.toml` versionado.
- *Alternativa considerada*: validação manual — rejeitada: pydantic dá mensagens de erro precisas de graça e já é padrão no ecossistema.

### D10. TUI: Textual com telas e workers
- Nome do aplicativo: `LiberLingua` configurado nos metadados da TUI.
- Telas: boas-vindas/primeira execução → configuração → seleção de livro (usando `DirectoryTree` com botão para subir de nível e navegar em qualquer diretório do sistema de arquivos, sem botões de atalho redundantes) → ajuda (modal acionável por atalho global `h`) → estimativa (confirmação) → progresso (por bloco, ETA vivo medido da vazão real, logs redigidos, cancelamento com Ctrl+C ordenado) → relatório final.
- Atalhos Globais: `q` para Sair, `c` para Configurações, `h` para Ajuda, centralizados na aplicação principal para navegação fluida sem poluição de botões nas telas individuais.
- Tradução roda em `Worker` do Textual; TUI nunca bloqueia. Interface em pt-BR.
- **Configuração de Modelo**: O campo de modelo na TUI é isolado por provedor. Se houver modelo configurado anteriormente para o provedor ativo, o dropdown exibe apenas esse modelo. Se for um provedor limpo, o dropdown exibe um aviso de teste obrigatório.
- **Fallback Dinâmico de Teste**: Se o teste de conexão retornar modelos da rota `/models`, o dropdown é populado dinamicamente com eles. Se a rota `/models` for inexistente ou vazia (retorno 404/405/501), o dropdown é ocultado e um campo de digitação manual é exibido. O salvamento valida a obrigatoriedade do modelo.
- **Localização**: A interface utiliza termos localizados em português, como "Provedor" em vez de "Provider".

### D11. Testes com cobertura máxima
- Domínio: 100% branch (gate por módulo). Adapters: API falsa com `respx` (sucesso, 429, timeout, resposta quebrada, usage). EPUB: fixtures douradas (livros miniatura) com byte-diff. Propriedade (`hypothesis`): `parse → serialize → parse` idempotente para XHTML arbitrário.
- Gate global ≥95% no CI (GitHub Actions: lint + testes + coverage). TUI: `textual.pilot` para os fluxos principais.
- *Por que a meta é atingível*: a arquitetura D1 empurra regras para funções puras.

## Risks / Trade-offs

- **[Contagem de tokens aproximada (tiktoken ≠ tokenizer DeepSeek)]** → o relatório pós-voo usa o usage exato da API; a diferença fica visível e absorvida pelo teto de gasto.
- **[Serialização lxml pode normalizar entidades/aspas em arquivos tocados]** → testes dourados fixam o comportamento; normalização é cosmética e aceitável nos capítulos traduzidos.
- **[keyring em Linux sem serviço secreto falha]** → fallback de arquivo cifrado com senha por sessão.
- **[AGPL afasta contribuidores comerciais]** → escolha deliberada do autor (radicalismo open source).
- **[TUI + PyInstaller exige hidden imports na fase 2]** → fase 2 terá workflow CI dedicado; não bloqueia a v1.
- **[Rate limits variáveis por provider]** → backoff adaptativo + `Retry-After`; ETA é medido, não chutado.

## Migration Plan

Greenfield: não há migração. Primeira versão = `0.1.0`. Estrutura de pacote pronta para hatch desde o dia 1 (`pyproject.toml`, `src/tradutor/`, `tests/`), para que a publicação PyPI/`uv tool` seja imediata.

## Open Questions

- Título traduzido: manter o original entre parênteses (ex.: "Código Limpo (Clean Code)") ou só a tradução? Decisão cosmética de política — não altera specs, design nem tasks.
- Detecção automática de idioma de origem: via heurística no texto (reconhecimento de palavras comuns) ou pergunta ao modelo na passada de priming? Detalhe de implementação da passada de priming.
