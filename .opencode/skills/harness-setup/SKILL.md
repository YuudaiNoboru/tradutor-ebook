---
name: harness-setup
description: Produz um plano de harness de engenharia (guides + sensors) calibrado ao contexto do projeto, baseado nos artigos "Harness Engineering for Coding Agent Users" e seu follow-up sobre sensores de manutenibilidade (Böckeler/Fowler). Agnóstica de linguagem — lê fundacao.md, arquitetura.html e outros artefatos do projeto para se situar, em vez de perguntar tudo do zero. Não implementa nada: gera um documento de plano (harness-plano.md) que serve de insumo para implementação via especificar-funcionalidade/modificacao-rapida + OpenSpec.
---

# Skill: Plano de Harness de Engenharia (Guides + Sensors)

Harness, no sentido deste artigo, é o sistema de controles em volta de um agente de código: **guides** (feedforward — orientam o agente antes de agir) e **sensors** (feedback — dão ao agente a chance de se autocorrigir depois de agir), cada um computacional (determinístico, rápido) ou inferencial (semântico, mais caro). O objetivo não é eliminar supervisão humana, é direcioná-la para onde ela importa mais.

Esta skill **não implementa nada**. Ela produz `harness-plano.md`: um diagnóstico do que existe, calibrado ao contexto real do projeto, e um plano priorizado de itens a implementar depois — a implementação de cada item acontece via `especificar-funcionalidade` ou `modificacao-rapida`, seguidas de OpenSpec, exatamente como qualquer outra mudança no projeto.

Esta skill é **agnóstica de linguagem**. Ela nunca prescreve uma ferramenta específica como a única opção — trabalha por categoria de sensor/guide, e usa `resources/exemplos-ferramentas.md` só como referência ilustrativa, nunca como lista fechada.

---

## 🔄 Quando Rodar

- **Em projeto novo:** logo depois de `fundacao-projeto` e da primeira geração do `architecture-report` — nesse ponto já existem características arquitetônicas priorizadas, estilo escolhido, regras de acoplamento documentadas e ADRs fundacionais, que alimentam diretamente o Architecture Fitness Harness (Passo 1). Rodar antes disso significaria inventar essas regras do zero, duplicando o que essas duas skills já produzem.
- **Em projeto existente:** ao adotar agentes de código, ou para auditar um harness incompleto. `fundacao.md`/`arquitetura.html` podem não existir — prossiga mesmo assim, mas avise o desenvolvedor que faltou essa base.
- **Repetidamente:** harness é prática contínua, não configuração única. Reaudite depois de padrões de erro repetidos, ou em uma cadência periódica (ligado ao item P2/P6 do diagnóstico) — cada rodada adiciona uma nova seção datada ao `harness-plano.md`, sem apagar o histórico.

---

## 🔄 Fluxo de Execução

### Passo 1: Explorar — Situar-se no Projeto

**1a. Ler primeiro os artefatos das outras skills, se existirem** — evita redescobrir o que já foi decidido:
- `fundacao.md` → problema/domínio (alimenta G2), características arquitetônicas priorizadas (base do Architecture Fitness Harness), estilo/particionamento/stack escolhidos (Seção 6 — define quais categorias de ferramenta fazem sentido), ADRs fundacionais (alimenta G3).
- `arquitetura.html` → Regras de Acoplamento por componente (traduzem quase diretamente em S6), ADRs aprovados (G3), papéis de usuário.
- `specs/` e `specs/rapidas/` → se existirem e estiverem em uso, G6 (spec antes de implementar) já está total ou parcialmente resolvido.
- `reviews/*.md` (da skill `code-review`) → procure padrões recorrentes nas seções de Bloqueador/Atenção entre reviews diferentes. Isso é evidência real de onde falta um sensor — não é teoria, é o que já deu errado. Use essa evidência no Passo 4.
- A própria existência de `especificar-funcionalidade`, `modificacao-rapida`, `code-review`, `architecture-report`, `fundacao-projeto` no projeto → conte como G6 e S7 (parcial ou total) já endereçados, e diga isso explicitamente no diagnóstico em vez de propor recriar o que já existe.

**1b. Ler o repositório**, sem assumir nomes de arquivo de um ecossistema específico — procure pela função, não pelo nome fixo:
- Arquivo de manifesto de dependências (qualquer que seja o formato do stack real, lido em `fundacao.md`)
- Guia de convenções existente (AGENTS.md, CLAUDE.md, ou equivalente)
- CI existente e o que ele roda
- Configs de linter, testes, checagem de tipos, se existirem
- Hooks de git
- Estrutura de pastas — módulos com limites claros?

**1c.** Se `fundacao.md` e `arquitetura.html` não existirem, prossiga mesmo assim, mas avise o desenvolvedor que essa base faltou e sugira rodar essas skills primeiro, se fizer sentido para o projeto.

### Passo 2: Entender o Contexto (interativa)

Pergunte ao desenvolvedor, uma pergunta por vez, aceitando respostas curtas:

| Pergunta | Por que importa |
|---|---|
| Qual o objetivo do projeto? (pessoal, trabalho, open-source, produção crítica) | Define o teto de investimento em harness |
| Quantas pessoas usam/mantêm? | Harness para 1 pessoa ≠ harness para 10 |
| Já está em produção? Tem usuários reais? | Sem produção, observabilidade é prematura |
| Qual a tolerância a downtime/bugs? | Define prioridade de E2E, SLOs, alertas |
| O agente de IA vai operar com quanta autonomia? | Mais autonomia → mais harness necessário |
| Os testes do projeto são majoritariamente gerados por IA sem revisão humana extensa? | Coverage alto não significa teste efetivo — isso muda a prioridade de S10 |
| Tem prazo/urgência? | Pode justificar adiar itens de baixo impacto |

Classifique cada exigência em três níveis: **Essencial** (sem isso o projeto está desprotegido no contexto dele), **Recomendado** (benefício claro, não urgente), **Provável over-engineering** (custo supera benefício neste contexto). Nunca remova um item unilateralmente — apresente a justificativa e deixe o desenvolvedor decidir.

### Passo 3: Diagnosticar

Preencha a tabela de `resources/harness-plano.md`. Para cada item já coberto por um artefato de outra skill (identificado no Passo 1), marque ✅ ou ⚠️ citando a fonte, em vez de tratá-lo como pendente.

### Passo 4: Priorizar

Ordem base por impacto/esforço: CI com lint/type/test → pre-commit hooks → coverage gate → logging estruturado + health check → fitness functions (S6) → dependency scan + dead code → E2E/approved fixtures → métricas + SLOs → mutation testing (S10) → mensagens acionáveis (P3) → template de harness → tracing + sensor contínuo.

Duas regras de ajuste sobre essa ordem:
- **Evidência de `reviews/*.md` sobe prioridade:** se um tipo de problema aparece repetidamente nos reviews, o item de harness que o teria pego sobe na lista — cite a contagem de ocorrências como justificativa.
- **Testes gerados por IA sem revisão elevam S10:** se a resposta à pergunta correspondente no Passo 2 for sim, mutation testing (S10) sobe de prioridade independente do nível de coverage atual — coverage mede execução, não verificação; um arquivo pode ter 100% de cobertura via um teste de ponta a ponta que nunca de fato verificou o comportamento daquele trecho.

Confirme a ordem final com o desenvolvedor — ele pode reordenar, pular itens ou adicionar urgências.

### Passo 5: Desenhar o Plano (documento, não implementação)

Para cada item aprovado, preencha um bloco no plano com:
- **Categoria de ferramenta** (nunca uma ferramenta específica — ver `resources/exemplos-ferramentas.md` como referência ilustrativa).
- **Orientação de autocorreção a embutir:** o que a mensagem do sensor deve dizer ao agente além de "falhou" — por que a regra existe, o que fazer. Uma mensagem de sensor bem escrita é um tipo positivo de prompt injection.
- **Válvula de escape graduada**, quando for regra de threshold (ex: tamanho de arquivo, complexidade): sob quais condições o agente pode ajustar o limite em vez de bloquear — nunca suprimir a regra para sempre, só destravar o caso atual, mantendo a regra viva para regressões futuras.
- **Mecanismo de verificação forçada**, para cada sensor: instruir via guia (menos confiável — na prática, agentes esquecem de checar sensores mesmo instruídos), hook após cada edição, git pre-commit hook (mais confiável para bloquear antes do commit), ou ferramenta custom exposta ao agente. Escolha e justifique por item, não genericamente.
- **Critério de aceite:** como confirmar depois que foi implementado corretamente. Esta skill não valida nada — quem faz isso é o `code-review` ou o desenvolvedor, depois da implementação via OpenSpec.

### Passo 6: Salvar

Salve como `harness-plano.md` na raiz do projeto. Não edite nenhum arquivo de configuração real (CI, linter, hooks) — esta skill só documenta.

### Passo 7: Handoff

Explique ao desenvolvedor:
- Itens pequenos (ex: "ligar linter no CI") → `modificacao-rapida` + OpenSpec.
- Itens estruturais (ex: "montar sensor contínuo com dashboard de status") → `especificar-funcionalidade` + OpenSpec.
- Depois de cada item implementado, `code-review` audita normalmente; se o item tocar componentes documentados, o próprio lembrete de atualizar `arquitetura.html` do `code-review` já cobre esse caso.

---

## 🛠️ Regras Gerais

- **Agnóstica de linguagem:** nunca prescreva uma ferramenta como única opção. Trabalhe por categoria; use `resources/exemplos-ferramentas.md` como referência, e pesquise na web quando o stack real não estiver coberto lá ou quando houver dúvida se o exemplo ainda é atual.
- **Não implementa nada:** o resultado desta skill é sempre um documento. Qualquer configuração real de ferramenta, CI ou hook acontece depois, via as skills de implementação.
- **Reaproveite antes de perguntar:** os artefatos das outras skills (`fundacao.md`, `arquitetura.html`, `specs/`, `reviews/`) quase sempre já respondem parte do diagnóstico — leia-os antes de tratar qualquer item como desconhecido.
- **Documento único por projeto:** `harness-plano.md` não é recriado do zero a cada execução — reauditorias adicionam uma nova seção datada, preservando o histórico de diagnóstico anterior.
- **Nunca remova um item do escopo unilateralmente:** "provável over-engineering" é uma sugestão com justificativa, a decisão final é sempre do desenvolvedor.
