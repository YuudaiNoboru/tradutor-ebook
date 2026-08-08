# Documento de Fundação: <NOME_DO_PROJETO>

*(gerado pela skill `fundacao-projeto` — decisões debatidas e escolhidas pelo desenvolvedor, não impostas pela IA)*

---

## 1. Problema & Domínio
*(preenchido com o desenvolvedor)*

### Qual problema este projeto resolve?
<Descrição objetiva>

### Para quem?
<Público-alvo / contexto de uso>

### Qual valor gera?
<O que muda pra quem usa, comparado a não ter esse projeto>

---

## 2. Atores & Ações (Levantamento Completo)
*(preenchido com o desenvolvedor — igual formato da especificar-funcionalidade, mas para o projeto inteiro, não uma feature)*

### Papéis de Usuário Envolvidos
<Todos os papéis/perfis distintos previstos, mesmo que a primeira versão não implemente todos>

### Ator: <Nome do Papel 1>
- **US-01:** Como <papel>, eu quero <ação> para que <objetivo>.

*(repetir bloco "Ator: <Nome do Papel>" para cada papel listado acima)*

### Ator: Sistema (Automações / Background)
- **SYS-01:** O sistema deve <ação automática/validação>.

### Ator: Desenvolvedor
- **DEV-01:** Como desenvolvedor, quero <ação/requisito>.

---

## 3. Características Arquitetônicas (-ilities)
*(debate — a IA apresenta candidatas, discute explícitas vs. implícitas, e propõe uma priorização; o desenvolvedor decide a lista final)*

### Explícitas (o que foi pedido)
- **[Característica]:** <de onde vem esse requisito>

### Implícitas (o que o domínio exige mesmo sem ter sido dito)
- **[Característica]:** <por que o domínio exige isso>

### Priorização Final (3 a 7 características "guia")
> O livro é claro: tentar otimizar tudo é como a arquitetura falha. Escolher poucas e ser honesto sobre o que fica em segundo plano.

1. <Característica> — <por quê é prioridade>
2. <Característica> — <por quê é prioridade>
3. ...

---

## 4. Estilo Arquitetural
*(debate — a IA propõe 2-3 estilos candidatos com prós/contras ligados diretamente à Seção 3, recomenda um e diz por quê; o desenvolvedor escolhe)*

### Opções Consideradas
- **[Estilo 1]:** <prós/contras frente às características priorizadas>
- **[Estilo 2]:** <prós/contras frente às características priorizadas>

### Escolha e Justificativa
> **Estilo escolhido:** <nome> — <por que atende melhor as características priorizadas da Seção 3>

---

## 5. Particionamento & Modularidade
*(debate — Package-by-layer vs. Package-by-feature vs. Package-by-component, e a estrutura de pastas inicial)*

### Estratégia de Particionamento Escolhida
> <Package-by-X> — <justificativa>

### Estrutura de Pastas Inicial
```text
<RAIZ_DO_PROJETO>/
├── <pasta_1>/
├── <pasta_2>/
└── ...
```

---

## 6. Stack Tecnológica
*(debate — cada escolha precisa ser justificada pelas características da Seção 3, nunca ao contrário)*

- **Linguagem:** <escolha> — <qual característica da Seção 3 essa escolha atende>
- **Frameworks/Bibliotecas principais:** <escolha> — <justificativa>
- **Banco de Dados / Persistência:** <escolha, ou "Nenhum nesta fase"> — <justificativa>
- **Outras tecnologias relevantes:** <ex: filas, cache, infra>

---

## 7. Risk Storming (opcional — Cap. 20)
*(mapear riscos arquiteturais logo na concepção, antes de qualquer código existir)*

| Risco | Componente/Área Afetada | Impacto (1-3) | Probabilidade (1-3) | Mitigação Proposta |
|---|---|---|---|---|
| <risco> | <área> | <1-3> | <1-3> | <mitigação> |

---

## 8. ADRs Fundacionais
*(um ADR por decisão relevante das Seções 4, 5 e 6 — não é opcional, são as decisões que sustentam tudo daqui pra frente)*

### ADR-01: <Título>
- **Contexto:** <problema/decisão a resolver>
- **Decisão:** <o que foi escolhido>
- **Consequências:** <impactos positivos e negativos>

*(repetir para cada decisão fundacional relevante)*

---

## 9. Scaffold Físico
*(o que foi efetivamente criado no disco nesta execução)*

- [ ] Estrutura de pastas da Seção 5 criada
- [ ] Arquivos de configuração mínimos criados (ex: `pyproject.toml`, `package.json`, `.gitignore`)
- [ ] Repositório Git inicializado (se aplicável)

> **Próximo passo:** este documento não gera `arquitetura.html` automaticamente. Rode a skill `architecture-report` a seguir para produzir o painel inicial a partir das decisões registradas aqui.
