---
name: code-review
description: Revisa a implementação de uma mudança do OpenSpec (entre Apply e Archive) checando conformidade com a especificação da funcionalidade (specs/<slug>.md ou, para correções e pequenas melhorias, specs/rapidas/<slug>.md) e com as decisões arquiteturais já registradas (arquitetura.html) — não redebate decisões, audita se foram seguidas.
---

# Skill: Revisão de Implementação (Conformidade, não Opinião)

Esta skill não é um linter nem um revisor de estilo genérico. Ela audita se o código implementado corresponde ao que já foi **decidido e aprovado** em duas fontes de verdade:

1. `specs/<slug-da-funcionalidade>.md` (formato completo, da `especificar-funcionalidade`) ou `specs/rapidas/<slug>.md` (formato reduzido, da `modificacao-rapida`) — o que foi decidido/descrito para esta mudança.
2. `arquitetura.html` — gerado pela skill `architecture-report`: regras de acoplamento entre componentes já registradas, ADRs aprovados anteriormente.

**Princípio central:** esta skill audita conformidade, não reabre debate arquitetural. Se uma decisão da spec ou do `arquitetura.html` parecer errada durante a revisão, isso é sinalizado como observação para o desenvolvedor decidir — a skill não a sobrescreve nem assume que está certa em discordar.

---

## 🔄 Quando Rodar

Entre o **Apply** e o **Archive** do OpenSpec. Se o relatório final tiver algum item na seção de Bloqueadores, o Archive não deve acontecer até que sejam corrigidos.

---

## 🔄 Fluxo de Execução

### Passo 1: Delimitar o Escopo
- Identifique a mudança do OpenSpec em questão (change-id) e o diff de arquivos que ela produziu — via `git diff` no que foi tocado pelo Apply, ou a listagem de arquivos do próprio diretório da change em `openspec/changes/<change-id>/`.
- Revise **apenas o que está no diff**. Não expanda o escopo para o restante do arquivo ou do módulo, salvo quando necessário para entender o contexto de uma linha alterada.

### Passo 2: Carregar as Fontes de Verdade
- Procure primeiro `specs/<slug>.md` (formato completo, da `especificar-funcionalidade`). Se existir, extraia: Atores/Ações (Seção 1), trade-offs aceitos (Seção 2), regras de acoplamento (Seção 3), fluxo e casos de borda (Seção 4), ADR proposta (Seção 5) e a checklist de Fitness Functions (Seção 6).
- Se não houver `specs/<slug>.md`, procure `specs/rapidas/<slug>.md` (formato reduzido, da skill `modificacao-rapida`). Se existir, extraia: o que muda, arquivos afetados, risco de regressão declarado e o resultado da Trava de Escalonamento. **Não cobre deste formato** uma checklist de Fitness Functions nem Casos de Borda formais — eles simplesmente não existem nesse tipo de registro, e não é um problema do diff. Ajuste o Passo 3 e o Passo 5 de acordo: sem Seção 6, não há item de Fitness Function para marcar como pendente.
- Se nenhum dos dois existir, prossiga o review sem checklist formal de aceite, mas deixe isso explícito no relatório — não finja que uma spec foi checada.
- Procure `arquitetura.html` na raiz do projeto. Se existir, extraia as regras de acoplamento e os ADRs dos componentes tocados pelo diff.
  - Se não existir, prossiga sem essa camada, e registre isso no relatório também.

### Passo 3: Auditar o Diff
Se a fonte for `specs/<slug>.md` (formato completo):
- **Contra a spec:** as ações dos Atores (US/DEV/SYS) descritas foram de fato implementadas? Os casos de borda debatidos na Seção 4 têm tratamento real (no código ou em teste)? A estrutura física bate com a Seção 3 (módulos criados/modificados no lugar certo)?
- **Contra o `arquitetura.html`:** o diff importa algo que a regra de acoplamento do componente proíbe? Contraria a decisão de algum ADR aprovado?
- **Fitness Functions da spec:** cada item da Seção 6 — está satisfeito, sim ou não, com base no que o diff mostra (não assuma; se não dá pra confirmar pelo diff, marque como não verificável e diga por quê).

Se a fonte for `specs/rapidas/<slug>.md` (formato reduzido):
- O diff corresponde ao que foi descrito em "O que muda"? Ficou maior ou diferente do escopo declarado?
- Se "Precisa de teste novo?" foi respondido "Sim", o teste existe no diff?
- **Contra o `arquitetura.html`:** mesmo assim, verifique se o diff viola alguma regra de acoplamento ou ADR já registrado — a Trava de Escalonamento da `modificacao-rapida` é uma autoavaliação do desenvolvedor no momento da spec, não substitui essa checagem aqui.

### Passo 4: Sinalizar Necessidade de Atualização Arquitetural
- Independente do resultado do Passo 3, verifique se o diff introduz componentes, regras de acoplamento ou uma decisão (a ADR proposta na Seção 5 da spec) que ainda não existem no `arquitetura.html`.
- Isso **não é um Bloqueador nem uma Atenção** — o `arquitetura.html` naturalmente não conhece ainda a funcionalidade que está sendo revisada agora. É só um lembrete registrado no relatório para rodar a skill `architecture-report` antes de começar a próxima funcionalidade, evitando que o dashboard fique defasado em relação ao código-fonte real.

### Passo 5: Classificar os Achados
Use três níveis — nunca misture um achado de conformidade com um achado de estilo:
- **🔴 Bloqueador:** viola uma regra de acoplamento registrada, contraria um ADR aprovado, ou deixa um item de Fitness Function sem implementação.
- **🟡 Atenção:** um caso de borda debatido na spec não tem tratamento visível, ou o comportamento diverge do fluxo lógico descrito sem justificativa aparente.
- **🔵 Sugestão:** qualidade geral fora do escopo de conformidade (nomes, duplicação, tratamento de exceção genérico) — não bloqueia o Archive.

Cada achado deve citar arquivo/trecho e apontar exatamente qual fonte ele viola (qual regra, qual ADR, qual item da Seção 6).

### Passo 6: Gerar o Relatório
- Preencha `resources/relatorio.md` com os achados.
- Salve como `reviews/<slug-da-funcionalidade>.md` — nunca sobrescreva o review de uma funcionalidade anterior usando sempre o mesmo nome de arquivo.
- Termine com um veredito claro: **PODE ARQUIVAR SEM RESSALVAS**, **PODE ARQUIVAR APÓS CORRIGIR BLOQUEADORES**, ou **NÃO ARQUIVAR**.

---

## 🛠️ Regras Gerais

- **Não redebater arquitetura:** se o diff segue fielmente uma decisão da spec ou do ADR que, na sua avaliação, foi uma má decisão, isso não é um Bloqueador — é uma observação separada, deixada para o desenvolvedor considerar numa próxima especificação.
- **Sem fonte, sem Bloqueador:** um achado só pode ser Bloqueador se apontar uma regra, ADR ou item de Fitness Function específico que ele viola. Sem isso, o máximo que pode ser é Sugestão.
- **Diff, não o projeto inteiro:** não transforme o review numa auditoria geral do módulo — mantenha o foco no que a mudança do OpenSpec efetivamente tocou.
- **Nomes de arquivo:** `reviews/<slug-da-funcionalidade>.md`, usando o mesmo slug do `specs/<slug>.md` correspondente, para ficar fácil de cruzar os dois.
