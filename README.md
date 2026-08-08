# tradutor-ebook

Tradutor de e-books EPUB para o português usando APIs de LLM com as suas
próprias chaves (BYOK). Feito para leitores brasileiros de livros técnicos
em inglês — preserva a formatação original do livro (negritos, itálicos,
títulos, código, tabelas) sem depender de ecossistemas fechados.

> **Estado:** funcional (v0.4.0). A interface TUI completa, suporte a provedores sem chaves e auto-atualização integrada no Windows já estão implementados e operacionais.

## O que faz

- **EPUB 2 e EPUB 3**: lê o container, segmenta o XHTML em blocos e
  reescreve o livro com cirurgia in-place — arquivos intocados ficam byte a
  byte idênticos, e só os nós de texto traduzidos mudam.
- **Duas famílias de providers**: LLMs com a sua própria chave (BYOK, ex.:
  DeepSeek) e tradutores automáticos comuns sem chave do usuário. Providers
  novos entram como módulos descobertos em `providers/llm/` ou
  `providers/machine_translation/`, sem registro central.
- **Proteção determinística**: código, SVG, MathML, `script` e `style` nunca
  são enviados ao modelo (extraídos como placeholders e restaurados).
- **Qualidade** (somente LLMs): passada de glossário (termos técnicos +
  nomes próprios em JSON editável à mão), passada de priming (estilo/tom do
  livro) e política de termos (traduzir / manter / híbrido — padrão).
  Tradutores comuns não oferecem glossário, priming ou política de termos.
- **Custo controlado**: estimativa pré-voo em US$, teto de gasto opcional e
  relatório final real-vs-previsto.
- **Retomada**: tradução por blocos com cache; interrupções retomam sem
  re-traduzir o que já foi feito.
- **Segurança**: chaves no cofre do sistema (keyring), fallback de arquivo
  cifrado e override por variável de ambiente; chaves nunca aparecem em
  logs e nunca atravessam o núcleo do domínio.
- **Interface em português**: TUI (Textual) com fluxo guiado — configuração,
  estimativa, progresso com ETA e relatório final.
- **Auto-atualizador automático (Windows)**: se o aplicativo estiver rodando como executável Windows compilado (frozen), ele verifica de forma assíncrona a existência de novas releases no GitHub na inicialização, baixa em segundo plano e realiza a substituição física e relançamento de forma atômica e segura.

## Requisitos

- Python 3.12+
- Gerenciado com [Hatch](https://hatch.pypa.io/)

## Instalação

### Como Executável Standalone (Windows)

Para usuários do Windows, não é necessário instalar o Python ou gerenciar dependências por linha de comando:
1. Acesse as [Releases do GitHub](https://github.com/YuudaiNoboru/tradutor-ebook/releases) do projeto.
2. Baixe o executável `tradutor.exe` da versão mais recente.
3. Execute o binário diretamente no terminal do Windows (`cmd` ou `PowerShell`).
*Nota: a partir da versão `v0.4.0`, o executável possui suporte a atualizações automáticas integradas.*

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
# ou direto do git (quando publicado)
uv tool install git+https://github.com/YuudaiNoboru/tradutor-ebook
```

Depois é só chamar:

```bash
tradutor
```

## Como usar

1. **Primeira execução**: o app guia a configuração da chave de API (vai
   para o cofre do sistema, nunca para o disco em texto claro) e testa a
   conexão com o provider.
2. **Selecione o livro**: escolha um arquivo `.epub` (EPUB 2 ou EPUB 3).
3. **Estimativa**: o app mostra o resumo do livro, a estimativa de custo em
   US$ e o tempo previsto antes de começar.
4. **Progresso**: barra por bloco com ETA vivo, logs redigidos e
   cancelamento ordenado (Ctrl+C). Interrupções retomam de onde pararam.
5. **Saída**: o livro traduzido fica ao lado do original como
   `livro-pt-BR.epub` (o original nunca é sobrescrito), com sumário, título
   e idioma atualizados e um apêndice com o glossário usado.
6. **Auto-atualizador**: No Windows executado como frozen, se uma nova versão for publicada no GitHub, o aplicativo detecta na inicialização e oferece o download em segundo plano. Após o download, convida a reiniciar para aplicar a nova versão de forma transparente e atômica.

Dica: o diretório de trabalho do livro guarda `estado.json` (cache de
retomada) e `glossario.json` (termos editáveis à mão — edite e re-traduza
para ver o efeito; somente LLMs). Em livros grandes, aumentar o paralelismo
(`execution.parallelism` no config, ex.: 8–10) acelera bastante — desde que
o seu plano no provider permita essas requisições simultâneas.

## Tradução automática experimental (Google Web)

Além dos LLMs BYOK, o app oferece a família `machine_translation` com o
provider experimental `google-web`, que usa endpoints não oficiais da
interface web do Google e **não exige chave do usuário**. Antes de usar,
saiba que:

- **É experimental**: o endpoint pode mudar, ser bloqueado ou deixar de
  funcionar sem aviso. Não há garantia de disponibilidade nem de gratuidade.
- **Sem qualidade estendida**: não há glossário, priming ou política de
  termos; a medição é de caracteres/blocos (tokens e custo não são
  reportados).
- **Limites conservadores**: os lotes, o atraso entre chamadas e a
  concorrência vêm da seção `[machine_translation]` do config e existem para
  reduzir o risco de bloqueio; interrupções retomam pelo cache.
- **Privacidade**: o texto dos capítulos é enviado ao serviço remoto — não
  traduza livros confidenciais.
- **Preservação validada**: respostas que alterarem markup ou placeholders
  são rejeitadas antes de gravar; a estrutura XHTML é validada bloco a bloco.

Na tela de configuração, escolha primeiro a família ("Tradução automática")
e depois o provider; chave, modelo e opções de glossário ficam ocultos para
essa família.

## Configuração

O arquivo de configuração fica no diretório padrão da plataforma
(`%APPDATA%` no Windows, `~/Library/Application Support` no macOS e
`~/.config` no Linux). Copie o exemplo para começar:

```bash
cp config.example.toml <diretório-de-configuração>/tradutor-ebook/config.toml
```

Chaves de API **não** ficam no arquivo de configuração: elas vão para o
cofre do sistema na primeira execução, com fallback de arquivo cifrado.
Você também pode definir `DEEPSEEK_API_KEY` no ambiente. Providers comuns
(`machine_translation`) não usam chave do usuário.

O campo `family` seleciona a família de provider (`llm`, padrão, ou
`machine_translation`); a seção `[machine_translation]` do exemplo traz os
limites conservadores do provider experimental.

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

## Versionamento e releases

O projeto usa versionamento semântico em fase 0.x: enquanto o MAJOR for
`0`, mudanças incompatíveis sobem o dígito MINOR (nunca o MAJOR). Na
prática:

- **Nova funcionalidade** → MINOR sobe e o PATCH volta a zero
  (0.2.3 → 0.3.0)
- **Apenas correções** → PATCH sobe (0.3.0 → 0.3.1)
- **Mudança incompatível em fase 0.x** → MINOR sobe (0.3.1 → 0.4.0)

A versão e as notas de release derivam dos commits convencionais via
[commitizen](https://commitizen-tools.github.io/commitizen/): o
`CHANGELOG.md` e o `__version__` em `src/tradutor/__init__.py` são gerados
pelo tooling e nunca devem ser editados à mão.

### Regras do repositório

- A branch `main` é protegida: mudanças entram apenas por pull request com
  checks aprovados, e o merge é somente por squash. Push direto é recusado
  até para o mantenedor.
- O título do PR vira o commit final (squash), então siga a convenção
  também nele.
- Commits e títulos de PR seguem `type: description`, com tipo reconhecido
  (`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`,
  `ci`, `chore`) e descrição livre em português — ex.:
  `feat: estimar custo antes de traduzir`.
- Após clonar, ative o hook local que recusa commits fora da convenção:

```bash
hatch run setup
```

### Como preparar uma release

Releases não são automáticas: o timing é decisão do mantenedor. Passo a
passo:

1. Crie a branch de release: `git switch -c release/v0.3.0 main`
2. Confira o que será liberado: `hatch run release -- --dry-run`
3. Gere versão e changelog (sem commitar nem criar tag):
   `hatch run release -- --files-only --yes`
4. Revise `src/tradutor/__init__.py`, `pyproject.toml` e `CHANGELOG.md` e
   commit como `chore(release): v0.3.0`
5. Abra o PR e merge por squash após os checks ficarem verdes
6. No commit do merge, crie a tag anotada e faça o push:
   `git tag -a v0.3.0 -m v0.3.0 <sha-do-merge>` e `git push origin v0.3.0`

O push da tag dispara o CI, que publica a GitHub Release com as notas
daquela versão extraídas do `CHANGELOG.md`.

## Licença

[AGPL-3.0](LICENSE) — este projeto permanece aberto em qualquer derivação,
inclusive SaaS.
