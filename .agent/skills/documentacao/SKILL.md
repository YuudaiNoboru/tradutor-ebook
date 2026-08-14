---
name: documentacao
description: Mantém README.md, guias de uso (docs/guias/) e — só quando o projeto não tiver ferramenta de changelog automatizada (Commitizen, semantic-release, etc.) — CHANGELOG.md (raiz, formato Keep a Changelog) atualizados a cada mudança finalizada. Reconcilia docs/specs/<slug>.md e docs/specs/rapidas/<slug>.md com o que foi de fato implementado — importante quando a ferramenta de Spec-Driven Development usada (ex: OpenSpec) arquiva o próprio estado interno sem atualizar as specs geradas por essas skills. Roda em modo leve a cada mudança e em modo de auditoria completa periodicamente. Não cobre docstrings/comentários inline.
---

# Skill: Documentação de Produto & Reconciliação de Specs

Duas responsabilidades, sempre as duas:

1. **Documentação de produto** — `README.md`, `CHANGELOG.md`, guias de uso em `docs/guias/`. Escrita na linguagem de quem usa o projeto, não de quem o construiu — reaproveitando as histórias de usuário (US-XX) do spec, nunca o diff técnico.
2. **Reconciliação de specs** — depois que uma mudança é implementada, `docs/specs/<slug>.md` ou `docs/specs/rapidas/<slug>.md` continuam sendo o plano *original*, não necessariamente o que foi de fato construído. Ferramentas de implementação (OpenSpec, Superpower, SDDD, etc.) arquivam o próprio estado interno, mas não têm por que saber que esses arquivos existem. Esta skill fecha esse buraco, anexando uma seção de reconciliação — nunca reescrevendo a decisão original.

Não cobre docstrings ou comentários inline no código — fora de escopo por decisão do desenvolvedor.

---

## 🔄 Quando Rodar

- **Modo Leve (a cada mudança):** depois que `code-review` finaliza uma mudança sem bloqueador. Atualiza só o que essa mudança específica afeta.
- **Modo Auditoria (periódico ou sob demanda):** varre README, CHANGELOG, guias e todas as specs em busca de defasagem acumulada — útil se o Modo Leve foi pulado, ou na mesma cadência de reauditoria do `harness-setup`.

---

## 🔄 Fluxo — Modo Leve

### Passo 0: Detectar se o CHANGELOG.md já é automatizado
Antes de tocar em `CHANGELOG.md`, verifique se o projeto já tem uma ferramenta gerando esse arquivo a partir de commits (Commitizen/`cz bump`, semantic-release, changesets, release-please, ou equivalente) — procure config dessas ferramentas (ex: `[tool.commitizen]` no `pyproject.toml`, `.releaserc`, `.changeset/`) e/ou instrução explícita em `AGENTS.md`/`CLAUDE.md` do tipo "não editar `CHANGELOG.md` à mão".

Se detectar automação: **pule o Passo 3 inteiro** para este projeto — não edite `CHANGELOG.md`. A entrada de changelog já vai sair do commit convencional na hora do release. Continue normalmente com Reconciliação de Spec (Passo 2) e README/Guias (Passo 4).

Se não detectar automação: siga o Passo 3 normalmente.

### Passo 1: Coletar o que Mudou
- Leia `docs/specs/<slug>.md` ou `docs/specs/rapidas/<slug>.md` correspondente à mudança.
- Leia `docs/reviews/<slug>.md` — o que o `code-review` encontrou, incluindo qualquer indicação de que a implementação divergiu do planejado.
- Leia o diff real da mudança.

### Passo 2: Reconciliar o Spec
- Compare o planejado (spec original) com o implementado (diff + review).
- Bateu exatamente → marque os itens de checklist/Fitness Functions como concluídos no próprio arquivo.
- Divergiu → **não reescreva a decisão original.** Anexe a seção "Reconciliação Pós-Implementação" (template em `resources/reconciliacao.md`) ao final do arquivo: o que mudou em relação ao planejado, e por quê — pergunte ao desenvolvedor se não estiver claro pelo diff/review.
- Isso evita que `docs/specs/` vire um documento de intenção congelado que nunca mais bate com a realidade.

### Passo 3: Atualizar CHANGELOG.md (só se não houver automação — ver Passo 0)
- Formato **Keep a Changelog**: seção `[Unreleased]` no topo, categorias `Added`/`Changed`/`Deprecated`/`Removed`/`Fixed`/`Security`.
- Escreva a entrada a partir das histórias de usuário (US-XX) do spec — o changelog é pro usuário do projeto, não pro desenvolvedor que o implementou.
- Uma entrada por mudança, na categoria certa. Se a mudança tocar mais de uma categoria, separe em entradas distintas.
- Template de entrada em `resources/reconciliacao.md`.

### Passo 4: Atualizar README.md e Guias
- Só se a mudança afeta o que já está documentado: recurso novo a mencionar, comportamento que mudou, novo requisito de instalação/configuração.
- Edite só a seção afetada — não reescreva o documento inteiro.
- Se a mudança introduziu algo que merece explicação própria (ex: novo fluxo de uso), avalie criar ou atualizar um arquivo em `docs/guias/`.

### Passo 5: Confirmar com o Desenvolvedor
Apresente um resumo do que foi atualizado (README, CHANGELOG, spec reconciliado, guias) antes de salvar — principalmente o texto do CHANGELOG, que vira registro público do projeto.

---

## 🔄 Fluxo — Modo Auditoria

1. Leia `README.md`, `docs/guias/*`, e todos os `docs/specs/*.md` e `docs/specs/rapidas/*.md`. Leia `CHANGELOG.md` só se o Passo 0 (detecção de automação) não tiver sido feito ainda nesta auditoria — repita a checagem, já que a automação pode ter sido adotada depois da última execução.
2. Para cada spec sem reconciliação (sem a seção "Reconciliação Pós-Implementação" nem checklist marcado), verifique contra o código atual se ainda está desatualizada e reconcilie.
3. Para README/guias, procure menções a comportamento que não existe mais, ou omissões de funcionalidades já existentes há tempo — cruze com `docs/arquitetura/arquitetura.html` (a Tabela Ator/Ação já documenta o que hoje existe).
4. Gere um relatório de itens defasados e proponha as atualizações uma por uma, para confirmação — não aplique tudo de uma vez sem revisão.

---

## 🛠️ Regras Gerais

- **`README.md` e `CHANGELOG.md` ficam na raiz do projeto** — convenção universal (GitHub e a maioria das ferramentas renderizam o README da raiz de forma especial), diferente das outras skills, que salvam tudo em `docs/`.
- **Nunca apaga o registro original da decisão:** reconciliação sempre soma uma seção nova ao final do spec, nunca substitui ou edita o conteúdo original.
- **Linguagem de usuário, não de implementação:** reaproveite as US do spec pro CHANGELOG/README; não descreva a mudança em termos de arquivos, classes ou funções internas.
- **Formato Keep a Changelog** para o `CHANGELOG.md` — **somente quando o projeto não tiver ferramenta de changelog automatizada** (Commitizen, semantic-release, changesets, etc.). Nunca edite um `CHANGELOG.md` mantido por automação — isso quebra o próximo release. Verifique isso a cada execução, não assuma o resultado da última vez.
- **Não cobre docstrings/comentários inline** — fora do escopo desta skill.