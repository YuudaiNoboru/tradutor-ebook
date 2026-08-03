# AGENTS.md — regras de fluxo para agentes de IA

Este arquivo é a fonte única das regras de fluxo do repositório para
qualquer agente de IA que trabalhe nele. `QWEN.md` e `GEMINI.md` apontam
para cá; o OpenCode lê este arquivo diretamente.

## Fluxo obrigatório

1. **Nunca faça push direto na `main`.** Toda mudança entra por branch +
   pull request, com merge apenas por squash. A regra vale também para o
   mantenedor.
2. **Commits e títulos de PR seguem conventional commits**:
   `type: description`, com tipo reconhecido (`feat`, `fix`, `docs`,
   `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`) e
   descrição livre em português. O hook `.githooks/commit-msg` recusa
   mensagens fora do padrão — após clonar, ative-o com `hatch run setup`.
3. **O título do PR é o commit final** (squash): deve seguir a convenção e
   resumir a mudança inteira.

## Arquivos nunca editados à mão

- `CHANGELOG.md` — gerado pelo `cz bump` a partir dos commits
  convencionais.
- O número de versão em `src/tradutor/__init__.py` (`__version__`) e em
  `[tool.commitizen] version` no `pyproject.toml` — atualizado apenas pelo
  `cz bump`.

## Releases (somente sob pedido do usuário)

Releases nunca são automáticas e só acontecem quando o usuário pedir
explicitamente. O fluxo:

1. Crie a branch `release/vX.Y.Z` a partir da `main`.
2. Confira antes: `hatch run release -- --dry-run`.
3. Gere versão e changelog sem commitar nem criar tag:
   `hatch run release -- --files-only --yes`.
4. Commit como `chore(release): vX.Y.Z` e abra o PR.
5. Após o merge por squash, crie a tag anotada no commit do merge
   (`git tag -a vX.Y.Z -m vX.Y.Z`) e faça o push da tag. O CI publica a
   GitHub Release com as notas do changelog.

## Validação antes do PR

Rode e deixe verdes: `hatch run lint`, `hatch run fmt-check` e
`hatch run cov` (gate de cobertura >= 95%).
