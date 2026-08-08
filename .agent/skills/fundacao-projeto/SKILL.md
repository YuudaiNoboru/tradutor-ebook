---
name: fundacao-projeto
description: Conduz a concepção arquitetural de um projeto novo, do zero (pasta vazia, sem código ainda), baseado no livro Fundamentos da Arquitetura de Software (Richards & Ford) — problema, atores, características arquitetônicas, estilo, modularidade, stack tecnológica e ADRs fundacionais. Complementa especificar-funcionalidade, modificacao-rapida, code-review e architecture-report, que assumem um projeto já existente.
---

# Skill: Fundação Arquitetural de Projeto Novo

Esta skill é o **passo zero** do ciclo de desenvolvimento — antes de existir qualquer feature, qualquer código, qualquer `arquitetura.html`. É onde as decisões que vão restringir (e habilitar) tudo o que vem depois são tomadas com intenção, em vez de acontecerem por acidente no primeiro commit.

Ela não gera o `arquitetura.html` — isso continua sendo trabalho exclusivo da skill `architecture-report`, rodada manualmente depois desta. Esta skill produz o **documento de fundação** (`resources/fundacao.md` preenchido) que serve de insumo para essa primeira geração.

---

## 🔄 Fluxo de Execução

Cada fase abaixo é um **debate**, no mesmo espírito da `especificar-funcionalidade`: a IA nunca decide sozinha e apresenta pronto — ela apresenta opções, recomenda uma com justificativa, e espera o desenvolvedor escolher. Não pule fases nem preencha uma fase adiantada com base em suposições da fase seguinte.

### Fase 1: Problema & Domínio (interativa)
Pergunte ao desenvolvedor: qual problema o projeto resolve, para quem, e que valor gera. Não avance sem isso — toda decisão técnica das fases seguintes precisa remeter a essa base.

### Fase 2: Atores & Ações — Levantamento Completo (interativa)
Diferente da `especificar-funcionalidade` (que mapeia só uma feature), aqui o levantamento é do projeto inteiro: todos os papéis de usuário previstos, mesmo que a primeira versão não implemente todos, mais Sistema e Desenvolvedor. Use o mesmo formato de US/SYS/DEV.

### Fase 3: Características Arquitetônicas (debate)
1. Liste características **explícitas** (o que foi pedido) e **implícitas** (o que o domínio exige mesmo sem ter sido dito).
2. Proponha uma priorização de **3 a 7 características "guia"**, com justificativa de por que cada uma entrou na lista — nunca proponha otimizar todas ao mesmo nível; isso é o erro mais citado pelo livro na origem de arquiteturas que falham.
3. Debate: apresente sua proposta de priorização, o porquê, e espere o desenvolvedor confirmar ou ajustar.

### Fase 4: Estilo Arquitetural (debate)
1. Com a priorização da Fase 3 em mãos, proponha **2-3 estilos candidatos** (monolito modular, microkernel, event-driven, microsserviços, space-based, etc.), com prós e contras de cada um **ligados diretamente às características priorizadas** — nunca proponha um estilo por popularidade ou hype.
2. Recomende um, com justificativa explícita.
3. Aguarde a escolha do desenvolvedor antes de seguir.

### Fase 5: Particionamento & Modularidade (debate)
1. Proponha a estratégia de particionamento (Package-by-layer, Package-by-feature ou Package-by-component), com prós/contras frente ao estilo escolhido na Fase 4.
2. Depois da escolha, desenhe a estrutura de pastas inicial.

### Fase 6: Stack Tecnológica (debate)
1. Para cada decisão (linguagem, frameworks/bibliotecas, banco de dados, outras tecnologias), proponha opções e recomende uma.
2. **Toda escolha precisa citar explicitamente qual característica da Fase 3 ela atende.** Se uma tecnologia não se justifica por nenhuma característica priorizada, isso é um sinal de alerta — diga isso ao desenvolvedor em vez de preencher silenciosamente.

### Fase 7: Risk Storming (opcional — Cap. 20 do livro)
1. Pergunte ao desenvolvedor se quer rodar esta fase agora ou pular.
2. Se sim: para cada componente/decisão relevante das Fases 4-6, levante riscos arquiteturais plausíveis, estime impacto e probabilidade (escala 1-3) e proponha mitigação.

### Fase 8: ADRs Fundacionais
Registre um ADR por decisão relevante das Fases 4, 5 e 6 — Contexto, Decisão, Consequências. Essas são as decisões que sustentam o projeto; não é uma etapa opcional, mesmo que o Risk Storming da Fase 7 tenha sido pulado.

### Fase 9: Scaffold Físico
1. Crie a estrutura de pastas definida na Fase 5 e os arquivos de configuração mínimos da stack escolhida na Fase 6 (ex: `pyproject.toml`, `package.json`, `.gitignore`).
2. Preencha `resources/fundacao.md` com todas as decisões das fases anteriores e salve como `fundacao.md` na raiz do projeto.
3. Avise explicitamente o desenvolvedor: **esta skill não gera `arquitetura.html`** — o próximo passo recomendado é rodar a skill `architecture-report`, que vai usar o código recém-criado e o `fundacao.md` como base para o primeiro painel de arquitetura.

---

## 🛠️ Regras Gerais

- **Debate em toda fase com mais de um caminho razoável** (Fases 3 a 6): opções, recomendação justificada, escolha do desenvolvedor — nunca a IA decide e apresenta pronto.
- **Stack justificada pelas características, nunca ao contrário:** se não dá pra apontar qual característica da Fase 3 uma escolha de tecnologia atende, isso é um sinal de que a escolha está sendo feita por preferência pessoal ou hype, não por arquitetura — sinalize isso ao desenvolvedor.
- **Não gera `arquitetura.html`:** essa é responsabilidade exclusiva da skill `architecture-report`, rodada manualmente depois desta.
- **Levantamento de Atores/Ações é completo aqui, não um esboço:** ao contrário de uma feature isolada, o projeto todo merece mapear tudo que já se consegue prever, mesmo que a primeira versão não implemente todos os papéis.
- **Nome do arquivo de saída:** sempre `fundacao.md` na raiz do projeto — é um documento único por projeto, não versionado por slug como `specs/`.
