# Documento de Fundação: tradutor-ebook

*(gerado pela skill `fundacao-projeto` — extração e documentação retroativa das decisões do projeto)*

**Modo:** Retroativo — reconstruído a partir de `arquitetura.html`, código em `src/tradutor` e configurações do projeto em 10/08/2026.

> **Nota de Confiança:** As Fases 2 a 6 e 8 abaixo são a reconstrução confirmada pelo desenvolvedor de decisões já implementadas no código, e não decisões tomadas no momento da escrita deste documento.

---

## 1. Problema & Domínio

### Qual problema este projeto resolve?
Leitores brasileiros de e-books técnicos em inglês não possuem uma ferramenta simples, flexível, segura e orientada a custo/qualidade para traduzir arquivos EPUB para o português sem perder a formatação original do livro (tags XHTML, blocos de código, tabelas, MathML, SVG) e sem depender de ecossistemas fechados ou serviços de assinatura caros.

### Para quem?
Leitores brasileiros de livros técnicos e literários em formato EPUB (estudantes, desenvolvedores, pesquisadores) que possuem suas próprias chaves de API em provedores de LLM (filosofia BYOK - Bring Your Own Key) ou que preferem traduções automáticas gratuitas sem chave.

### Qual valor gera?
- **Autonomia & Privacidade:** Chaves de API gerenciadas pelo usuário no cofre do sistema (keyring) ou tradução automática sem chave; credenciais nunca cruzam o domínio principal nem vão para discos ou logs em texto claro.
- **Fidelidade de Formatação:** Preservação rigorosa e determinística de código e markup XHTML por cirurgia in-place (placeholders determinísticos).
- **Controle de Custo:** Estimativa pré-voo em tokens/US$ e tempo (ETA), com relatórios detalhados ao final da execução.
- **Resiliência:** Cache de blocos (`estado.json`) que permite pausar e retomar traduções sem gastar tokens duplicados.
- **Qualidade Customizável:** Passadas de glossário e priming estilístico para provedores LLM.

---

## 2. Atores & Ações (Levantamento Completo)

### Papéis de Usuário Envolvidos
- **Leitor (Usuário Final):** Utiliza a TUI para configurar credenciais, selecionar livros, estimar custos, acompanhar e retomar a tradução.
- **Sistema (Automações / Background):** Processa arquivos EPUB, isola nós XML, gerencia requisições assíncronas concorrentes com rate limit, valida respostas e lida com atualização do aplicativo.
- **Desenvolvedor (Mantenedor):** Mantém o repositório, executa suítes de testes/cobertura, formata código e prepara releases semânticas.

---

### Ator: Leitor (Usuário Final)

- **US-01:** Como leitor, quero ser guiado na primeira execução para salvar minha chave de API de forma segura e testar a conexão com o provedor.
- **US-02:** Como leitor, quero configurar o provedor (LLM BYOK ou Tradução Automática), modelo, idioma de destino e nível de paralelismo.
- **US-03:** Como leitor, quero navegar pelo sistema de arquivos local e escolher o arquivo `.epub` a ser traduzido.
- **US-04:** Como leitor, quero ver uma estimativa pré-voo detalhada de tokens, custo em US$ e tempo antes de iniciar a tradução.
- **US-05:** Como leitor, quero acompanhar o progresso em tempo real com barra de progresso, relógio de ETA vivo e logs sanitizados.
- **US-06:** Como leitor, quero poder cancelar a tradução a qualquer momento mantendo o progresso salvo em cache local para retomada futura.
- **US-07:** Como leitor, quero consultar e editar manualmente o glossário gerado em `glossario.json` para re-traduzir termos específicos com LLMs.
- **US-08:** Como leitor no Windows, quero ser notificado sobre novas versões do aplicativo e ter a atualização baixada e instalada de forma transparente e atômica.

---

### Ator: Sistema (Automações / Background)

- **SYS-01:** O sistema deve validar a integridade do container EPUB 2/3 e desconstruir a estrutura XHTML preservando arquivos não-texto intocados.
- **SYS-02:** O sistema deve extrair nós de código, `script`, `style`, SVG e MathML substituindo-os por placeholders determinísticos que nunca são enviados aos provedores de tradução.
- **SYS-03:** O sistema deve enviar requisições assíncronas concorrentes respeitando limites de rate limit e limites configurados de concorrência.
- **SYS-04:** O sistema deve validar a resposta dos provedores garantindo que nenhum placeholder ou marcação XHTML foi corrompida antes de gravar o bloco.
- **SYS-05:** O sistema deve salvar periodicamente o progresso em `estado.json` permitindo retomada exata do ponto de interrupção.
- **SYS-06:** O sistema deve criptografar chaves no keyring nativo do sistema operacional e utilizar o `KeyringFallback` (AES) caso o serviço nativo não esteja disponível.
- **SYS-07:** O sistema deve checar releases no GitHub em segundo plano no Windows congelado e realizar a substituição física do executável via script atômico no relançamento.

---

### Ator: Desenvolvedor (Mantenedor)

- **DEV-01:** Como desenvolvedor, quero rodar suítes de testes unitários e de integração com verificação de cobertura (gate >= 95%).
- **DEV-02:** Como desenvolvedor, quero formatar e verificar o código com Ruff e hooks do Git (`.githooks/commit-msg`).
- **DEV-03:** Como desenvolvedor, quero preparar versões semânticas (`cz bump`) e automatizar a geração de changelog sem alterar o histórico manualmente.

---

## 3. Características Arquitetônicas (-ilities)

### Explícitas (Requisitos Diretos)
- **Fidelidade do Markup (Integridade Estrutural):** Preservar a estrutura interna do EPUB e do XHTML sem alterar formatação original, código ou marcadores visuais.
- **Transparência & Previsibilidade de Custos:** Exibir estimativas de tokens/gastos em dólares antes da execução de requisições pagas.
- **Usabilidade:** Interface TUI interativa, responsiva e amigável com suporte a navegação por arquivos.

### Implícitas (Exigências do Domínio)
- **Segurança & Privacidade de Credenciais:** Chaves de API nunca devem ser vazadas em logs, persistidas em texto claro ou expostas ao núcleo do domínio.
- **Resiliência & Tolerância a Falhas:** Capacidade de recuperar traduções interrompidas via cache, lidar com rate-limits e quedas de conexão.
- **Portabilidade:** Execução no Windows (executável standalone), macOS e Linux sem alterações de código-fonte.
- **Testabilidade & Manutenibilidade:** Cobertura de código estrita (gate >= 95%) e separação clara de responsabilidades (Arquitetura Hexagonal).

### Priorização Final (5 Características Guia)

1. **Fidelidade do Markup:** Inegociável — uma tradução que destrói a formatação de um livro técnico invalida o produto.
2. **Segurança & Privacidade:** Crucial — lidar com credenciais do usuário exige zero tolerância a vazamentos.
3. **Resiliência (Cache / Retomada):** Essencial — chamadas a LLMs são caras e propensas a interrupções de rede; o progresso deve ser persistente.
4. **Testabilidade & Manutenibilidade:** Fundamental — arquitetura hexagonal rigorosa com testes automatizados (>= 95% cobertura) para sustentabilidade.
5. **Usabilidade & Portabilidade (TUI / Executável Standalone):** Proporcionar uma experiência fluida no terminal e facilitar distribuição para usuários finais.

---

## 4. Estilo Arquitetural

### Opções Consideradas
- **Monolito Script Único (Procedural):** Simples inicialmente, mas impraticável para testabilidade, isolamento de chaves, múltiplos provedores e TUI reativa.
- **Microsserviços:** Complexidade excessiva e desnecessária para uma ferramenta CLI/TUI de uso local desktop/terminal.
- **Arquitetura Hexagonal (Ports & Adapters) / Monolito Modular:** Isolamento total do núcleo de domínio de I/O, UI e provedores HTTP.

### Escolha e Justificativa
> **Estilo escolhido:** Arquitetura Hexagonal (Ports & Adapters) em estrutura de Monolito Modular.
> **Justificativa:** Garante que as regras de negócio (`domain/`), a proteção do markup (`epub/`) e a orquestração (`translate/`) sejam 100% independentes de bibliotecas de UI (Textual), provedores HTTP (`httpx`) ou armazenamentos de credenciais (`keyring`). Isso permite testar 95%+ do código com mocks puros e trocar/adicionar provedores ou interfaces sem impactar o domínio.

---

## 5. Particionamento & Modularidade

### Estratégia de Particionamento Escolhida
> **Package-by-component / Hexagonal Ports & Adapters** — Organização por responsabilidade de arquitetura hexagonal.

### Estrutura de Pastas Inicial
```text
src/tradutor/
├── domain/            # Entidades puras (Book, Block, Glossary, PriceEstimate) e regras de negócio
├── epub/              # Container EPUB, parsing XHTML, extração e restauração de placeholders
├── translate/         # Engine de tradução assíncrona, orquestrador, cache de estado e rate limiter
├── providers/         # Adapters para provedores de tradução
│   ├── llm/           # Provedores LLM BYOK (DeepSeek, OpenAI, etc.)
│   └── machine_translation/ # Provedores de tradução automática sem chave (google-web)
├── infra/             # Adapters de infraestrutura (Keyring, KeyringFallback AES, config TOML, auto-update)
├── tui/               # Interface gráfica de terminal reativa (Textual - screens, widgets)
└── cli.py             # Ponto de entrada CLI/TUI
```

---

## 6. Stack Tecnológica

- **Linguagem:** Python 3.12+ (tipagem estática forte via Annotations, concorrência assíncrona nativa `asyncio`).
- **TUI Framework:** Textual (atende Usabilidade e Responsividade na TUI).
- **Processamento XML/EPUB:** `lxml` e `ebooklib` (atende Fidelidade do Markup com parsing rápido e cirurgia in-place).
- **HTTP Assíncrono:** `httpx` (atende Resiliência e Desempenho em chamadas concorrentes).
- **Tokenização:** `tiktoken` (atende Transparência de Custos em estimativas pré-voo).
- **Gerenciamento de Segredos:** `keyring` + `cryptography` (atende Segurança e Privacidade com cofre do OS + fallback AES).
- **Validação de Schemas:** `pydantic` (atende Manutenibilidade e Integridade de dados de configuração e glossários).
- **Tooling de Build/Testes:** Hatch (`pytest`, `coverage` com gate >= 95%, `hypothesis`, `ruff`, `commitizen`, `pyinstaller`).

---

## 7. Risk Storming (Capítulo 20)

| Risco | Componente / Área Afetada | Impacto (1-3) | Probabilidade (1-3) | Mitigação Proposta |
|---|---|---|---|---|
| Quebra de contrato no provider experimental `google-web` | `providers/machine_translation/` | 2 | 3 | Isolamento em adapter separado, aviso de status experimental na TUI, tratamento robusto de erros e retentativas. |
| Corrupção de tags XHTML/placeholders por LLM | `epub/` / `translate/` | 3 | 2 | Extração determinística de placeholders antes do envio; validação de integridade pós-resposta; rejeição e retentativa em caso de falha de parse. |
| Indisponibilidade de Keyring nativo (ambientes headless/Linux) | `infra/secrets.py` | 2 | 2 | Implementação de `KeyringFallback` usando criptografia AES via `cryptography` e variáveis de ambiente. |
| Falha no auto-update do executável Windows em execução | `infra/update.py` | 3 | 1 | Substituição física através de processo auxiliar isolado com validação prévia de SHA256 do binário baixado. |

---

## 8. ADRs Fundacionais

### ADR-001: Adotar Arquitetura Hexagonal com Separação Estrita de Domínio e Adapters
- **Contexto:** Necessidade de garantir testabilidade alta (gate >= 95%) e isolamento total entre regras de negócio, interface de usuário e chamadas externas de API.
- **Decisão:** O módulo `domain/` não depende de nenhuma biblioteca externa ou adapter de I/O. Credenciais e chaves de API nunca passam pelo modelo de domínio.
- **Consequências:** Arquitetura limpa, alta testabilidade com mocks, facilidade para adicionar novos provedores ou UIs.

### ADR-002: Proteção Determinística de Markup por Placeholders
- **Contexto:** Modelos de linguagem podem alterar, omitir ou corromper marcadores XHTML, nós de código e estilos durante a tradução.
- **Decisão:** Todo elemento que não deve ser traduzido (`<code>`, `<script>`, `<style>`, `<svg>`, `<math>`) é extraído e substituído por tokens determinísticos (ex: `[[[CODE_0]]]`) antes do envio ao provedor e restaurado após a resposta.
- **Consequências:** Garantia de 100% de integridade estrutural e de formatação nos livros traduzidos.

### ADR-003: Interface TUI Reativa com Executável Standalone para Windows
- **Contexto:** Proporcionar uma experiência interativa rica no terminal para usuários técnicos e disponibilizar um binário portátil sem dependência de instalação do Python para usuários Windows.
- **Decisão:** Utilizar Textual para a TUI e empacotar via PyInstaller para Windows, com auto-atualizador integrado via GitHub Releases.
- **Consequências:** Excelente usabilidade cross-platform e distribuição simplificada no Windows.

### ADR-004: Armazenamento Criptografado de Chaves de API via Keyring e Fallback AES
- **Contexto:** Garantir a segurança das chaves de API dos usuários (BYOK) de forma multiplataforma.
- **Decisão:** Priorizar o cofre do sistema operacional (`keyring`). Caso esteja indisponível, utilizar arquivo local cifrado via `cryptography` (AES-GCM).
- **Consequências:** Nenhuma chave salva em texto claro no disco, com suporte gracioso em ambientes onde o keyring nativo falhar.

### ADR-005: Suporte Dual a Famílias de Provedores (BYOK LLM e Tradução Automática sem Chave)
- **Contexto:** Permitir uso de LLMs de alta qualidade com personalização (glossário/priming) e opções gratuitas/sem chave de API.
- **Decisão:** Criar duas famílias de provedores (`llm` e `machine_translation`), compartilhando a mesma interface de adaptador de tradução.
- **Consequências:** Extensibilidade para novos provedores sem alterar o motor de orquestração.

---

## 9. Reconciliação do Documento & Scaffold Físico

- [x] Estrutura de pastas da Seção 5 verificada e mapeada em `src/tradutor/`
- [x] Arquivos de configuração de infraestrutura e build validados (`pyproject.toml`, `AGENTS.md`, `.gitignore`)
- [x] Repositório Git e convenções de commit verificadas
- [x] Documento salvo em `docs/fundacao/fundacao.md`

> **Aviso Importante:** Esta skill documenta a fundação arquitetural do projeto e **não gera `arquitetura.html` automaticamente**. O próximo passo recomendado é rodar a skill `architecture-report` para atualizar ou gerar o painel interativo de arquitetura com base no código e neste documento de fundação.
