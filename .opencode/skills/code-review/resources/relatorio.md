# Relatório de Review: <NOME_DA_FUNCIONALIDADE>

*(preenchido pela IA — referência: `specs/<slug>.md` e `arquitetura.html`, se existirem)*

---

## 1. Escopo Revisado

- **Mudança OpenSpec:** `<change-id>`
- **Spec de referência:** `specs/<slug>.md` <se não existir, dizer explicitamente: "Nenhuma spec encontrada — review feito sem checklist de aceite formal">
- **Arquivos tocados no diff:**
  - `<arquivo_1>`
  - `<arquivo_2>`

---

## 2. 🔴 Bloqueadores
*(viola regra de acoplamento do `arquitetura.html`, contraria um ADR aprovado, ou deixa um item da checklist de Fitness Functions da spec sem implementação — o Archive não deveria acontecer com itens aqui)*

- [ ] **[arquivo:linha]** <descrição do problema> — viola <fonte: qual regra de acoplamento / ADR-XX / item da Seção 6 da spec>

*(se não houver nenhum, escrever: "Nenhum bloqueador encontrado.")*

---

## 3. 🟡 Atenção
*(caso de borda da Seção 4 da spec sem tratamento visível no código ou em teste; comportamento que diverge do fluxo descrito na Seção 4 da spec sem ser claramente uma melhoria)*

- [ ] **[arquivo:linha]** <descrição> — relacionado a <qual caso de borda / qual passo do fluxo lógico>

*(se não houver nenhum, escrever: "Nenhum ponto de atenção encontrado.")*

---

## 4. 🔵 Sugestões
*(qualidade geral fora do escopo de conformidade: nomes, duplicação, tratamento de exceção genérico, legibilidade — não bloqueiam o Archive)*

- **[arquivo:linha]** <sugestão e por quê>

---

## 5. Checklist de Fitness Functions (da spec)
*(só se aplica se a fonte for `specs/<slug>.md`, formato completo — copiar os itens da Seção 6 e marcar cada um com base no diff, sem redebater se o critério em si faz sentido, só checar se foi atendido. Se a fonte for `specs/rapidas/<slug>.md`, escrever "N/A — modificação rápida, sem checklist de Fitness Functions" e usar o campo "Precisa de teste novo?" do modelo-rapido no lugar.)*

- [ ] Coesão & Isolamento
- [ ] Acoplamento Limpo
- [ ] Tratamento de Exceções
- [ ] Contrato Tipado
- [ ] Sem Hardcode

---

## 6. Conformidade Arquitetural (do `arquitetura.html`, se existir)

- **Regras de Acoplamento respeitadas?** <sim/não + detalhe>
- **ADRs relevantes:** <ADR-XX citado, e se o diff está alinhado ou não>

---

## 7. Lembrete de Atualização Arquitetural
*(o code-review NÃO atualiza o `arquitetura.html` — só sinaliza se é hora de rodar o `architecture-report`)*

- Esta mudança introduz componente(s), regra(s) de acoplamento ou ADR novos que ainda não estão no `arquitetura.html`? <sim/não>
- <Se sim: "Rode a skill `architecture-report` antes de começar a próxima funcionalidade, para evitar que o dashboard fique desatualizado.">

---

## 8. Veredito

<PODE ARQUIVAR (Archive) SEM RESSALVAS | PODE ARQUIVAR APÓS CORRIGIR BLOQUEADORES | NÃO ARQUIVAR>
