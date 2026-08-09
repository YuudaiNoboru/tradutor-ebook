---
name: modificacao-rapida
description: Documenta rapidamente uma correção de bug ou pequena melhoria antes da implementação via OpenSpec — sem debate de trade-offs nem ADR. Skill separada e explícita: o desenvolvedor a chama diretamente quando já sabe que a mudança é pequena, em vez de usar especificar-funcionalidade.
---

# Skill: Modificação Rápida (Bugfix / Pequena Melhoria)

Complementa a `especificar-funcionalidade`, não a substitui. Aquela é para **novas funcionalidades**, com debate arquitetural completo (Etapa 2, opções + recomendação + escolha do desenvolvedor, ADR, Fitness Functions). Esta é para **correções de bug e pequenas melhorias** que não introduzem decisão arquitetural nova.

**A escolha de qual skill chamar é sempre do desenvolvedor.** Esta skill não tenta adivinhar ou classificar automaticamente se a mudança é "pequena" — parte do princípio de que você já fez essa escolha ao chamá-la explicitamente. O único lugar onde ela questiona essa escolha é a Trava de Escalonamento do Passo 2, e mesmo assim como sugestão, não como decisão unilateral.

---

## Fluxo de Trabalho

### Passo 1: Coletar o Essencial
Pergunte ao desenvolvedor:
1. **O que muda** — comportamento atual vs. esperado, em poucas frases.
2. **Por quê** — bug reportado, dívida técnica pontual, ajuste de UX, mudança de configuração, etc.
3. **Arquivos/módulos afetados** — se o desenvolvedor já souber; senão, inspecione o código para localizar.

Não faça perguntas de Atores/Ações no formato da `especificar-funcionalidade` — isso é excesso de processo para o escopo desta skill.

### Passo 2: Trava de Escalonamento
Antes de preencher o modelo, verifique contra o `arquitetura.html` na raiz do projeto, se ele existir:
- Isso introduz um Ator/papel de usuário novo?
- Cria ou muda uma regra de acoplamento entre componentes já registrada?
- Contraria ou exige revisar um ADR aprovado?
- Muda comportamento observável de um jeito que pareça merecer uma decisão arquitetural registrada?

Se qualquer resposta for **sim**: pare e avise claramente o desenvolvedor que a mudança parece maior do que uma modificação rápida, e recomende rodar `especificar-funcionalidade` em vez desta. Isso é uma sugestão — se o desenvolvedor confirmar que quer seguir mesmo assim pela via rápida, respeite e continue, mas registre isso no modelo preenchido.

Se `arquitetura.html` não existir, pule esta checagem e avise que não foi possível verificar contra decisões arquiteturais existentes.

### Passo 3: Preencher e Salvar
Preencha `resources/modelo-rapido.md` com as respostas do Passo 1 e o resultado da Trava do Passo 2.
Salve como `specs/rapidas/<slug-da-mudanca>.md` — pasta separada de `specs/`, para que o `code-review` reconheça que é um registro no formato reduzido e ajuste suas expectativas (sem cobrar checklist de Fitness Functions ou Casos de Borda, que não existem aqui).

### Passo 4: Handoff para o OpenSpec
Apresente o resumo final ao desenvolvedor. Após confirmação, prossiga normalmente para a implementação via OpenSpec.

---

## Regras Gerais
- Nunca debate trade-offs nem propõe ADR — isso é escopo exclusivo da `especificar-funcionalidade`.
- Nome do arquivo de saída sempre em `specs/rapidas/<slug>.md`, nunca reaproveitando o caminho `specs/<slug>.md` (reservado para o fluxo completo).
- Template a ser preenchido: `resources/modelo-rapido.md`, dentro da pasta desta skill.
