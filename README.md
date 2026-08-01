# tradutor-ebook

Tradutor de e-books EPUB para o português usando APIs de LLM com as suas
próprias chaves (BYOK). Feito para leitores brasileiros de livros técnicos
em inglês — preserva a formatação original do livro (negritos, itálicos,
títulos, código, tabelas) sem depender de ecossistemas fechados.

> **Estado:** em desenvolvimento (v0.1). A interface completa ainda não está
> pronta; este repositório está na fase de estruturação do projeto.

## O que faz

- **EPUB 2 e EPUB 3**: lê o container, segmenta o XHTML em blocos e
  reescreve o livro com cirurgia in-place — arquivos intocados ficam byte a
  byte idênticos, e só os nós de texto traduzidos mudam.
- **Proteção determinística**: código, SVG, MathML, `script` e `style` nunca
  são enviados ao modelo (extraídos como placeholders e restaurados).
- **Qualidade**: passada de glossário (termos técnicos + nomes próprios em
  JSON editável à mão), passada de priming (estilo/tom do livro) e política
  de termos (traduzir / manter / híbrido — padrão).
- **Custo controlado**: estimativa pré-voo em US$, teto de gasto opcional e
  relatório final real-vs-previsto.
- **Retomada**: tradução por blocos com cache; interrupções retomam sem
  re-traduzir o que já foi feito.
- **Segurança**: chaves no cofre do sistema (keyring), fallback de arquivo
  cifrado e override por variável de ambiente; chaves nunca aparecem em
  logs e nunca atravessam o núcleo do domínio.
- **Interface em português**: TUI (Textual) com fluxo guiado — configuração,
  estimativa, progresso com ETA e relatório final.

## Requisitos

- Python 3.12+
- Gerenciado com [Hatch](https://hatch.pypa.io/)

## Instalação

### Durante o desenvolvimento

```bash
hatch env create     # cria o ambiente com dependências de dev
hatch run test       # testes
hatch run cov        # testes + gate de cobertura (>= 95%)
hatch run lint       # ruff check
```

### Como ferramenta (fase 1 — distribuição)

```bash
# a partir do repositório
uv tool install .
# ou com pipx
pipx install .
```

Depois é só chamar:

```bash
tradutor
```

## Configuração

O arquivo de configuração fica no diretório padrão da plataforma
(`%APPDATA%` no Windows, `~/Library/Application Support` no macOS e
`~/.config` no Linux). Copie o exemplo para começar:

```bash
cp config.example.toml <diretório-de-configuração>/tradutor-ebook/config.toml
```

Chaves de API **não** ficam no arquivo de configuração: elas vão para o
cofre do sistema na primeira execução, com fallback de arquivo cifrado.
Você também pode definir `DEEPSEEK_API_KEY` no ambiente.

## Desenvolvimento

```bash
hatch run fmt        # formata com ruff
hatch run fmt-check  # confere formatação
hatch run lint       # lint
hatch run cov        # testes + cobertura (gate >= 95%)
```

Arquitetura hexagonal: `domain/` (regras puras), `epub/`, `translate/`,
`providers/`, `infra/` e `tui/`. O núcleo nunca importa adapters, e o
domínio nunca recebe chaves.

## Licença

[AGPL-3.0](LICENSE) — este projeto permanece aberto em qualquer derivação,
inclusive SaaS.
