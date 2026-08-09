<!--
INSTRUÇÕES PARA O AGENTE DE IA:
1. Leia o mapeamento de Atores e Ações fornecido pelo desenvolvedor na Seção 1.
2. Inspecione o projeto atual (estrutura de pastas, acoplamentos, tratamento de erros, ADRs anteriores) antes de preencher qualquer coisa.
3. Preencha as Seções 2 a 6 com base em "Fundamentos da Arquitetura de Software" (Richards & Ford).
4. Adapte a Seção 4 (Casos de Borda) à plataforma real do projeto — Web, Mobile, Desktop ou Microserviços/Cloud.
5. Apresente o documento completo para debate e aprovação do desenvolvedor antes de gerar qualquer código.
-->

# Especificação da Funcionalidade: <NOME_DA_FUNCIONALIDADE>

---

## 1. Entrada do Desenvolvedor: Mapeamento de Atores & Ações
*(preenchido pelo desenvolvedor — a IA não escreve nesta seção)*

### Contexto / Objetivo Resumido
<Breve frase sobre o que é a funcionalidade>

### Papéis de Usuário Envolvidos
<Liste todos os papéis/perfis de usuário distintos que interagem com esta funcionalidade — ex: Comprador, Estoquista, Gerente. Se houver apenas um tipo de usuário, liste só ele.>

### Ator: <Nome do Papel 1>
- **US-01:** Como <papel>, eu quero <ação> para que <objetivo>.

### Ator: <Nome do Papel 2>
*(repita este bloco "Ator: <Nome do Papel>" para cada papel de usuário listado acima — apague se houver só um papel)*
- **US-02:** Como <papel>, eu quero <ação> para que <objetivo>.

### Ator: Desenvolvedor
- **DEV-01:** Como desenvolvedor, quero <ação/requisito>.

### Ator: Sistema (Automações / Background)
- **SYS-01:** O sistema deve <ação automática/validação>.

---

## 2. Análise Arquitetônica & Trade-offs
*(preenchido pela IA)*

### Características Arquitetônicas Críticas (-ilities)
- **[Característica 1]:** <Como a funcionalidade atende esta métrica no projeto>
- **[Característica 2]:** <Como a funcionalidade atende esta métrica no projeto>

### Trade-offs Aceitos
> **Decisão de Trade-off:** <O que está sendo sacrificado em prol de quê — ex: simplicidade vs desempenho, uso de RAM vs I/O de disco — considerando as restrições do ambiente/SO>

---

## 3. Estrutura Física & Módulos
*(preenchido pela IA)*

### Mapeamento no Projeto Existente
```text
<RAIZ_DO_PROJETO>/
├── <pasta_existente>/
│   └── <arquivo_a_modificar>.ext    <-- [MODIFICADO]
└── <nova_pasta_se_necessario>/      <-- [NOVO COMPONENTE COESO]
    ├── __init__.py
    ├── <modulo_logica>.py
    └── <modulo_adaptador>.py
```

### Regras de Acoplamento & Limites
- **Pode Importar:** <Módulos internos permitidos>
- **NÃO Pode Importar:** <Importações proibidas para evitar acoplamento indevido>
- **Padrão de Comunicação:** <Padrão escolhido — ex: Injeção de Dependência, Eventos de Domínio, Interfaces>

---

## 4. Fluxo de Execução & Casos de Borda
*(preenchido pela IA)*

### Sequência Lógica
1. **[Disparo]:** <Gatilho>
2. **[Processamento]:** <Lógica principal>
3. **[Fronteira Externa/I/O]:** <Interação com rede/SO/banco>
4. **[Finalização]:** <Atualização de estado / retorno>

### Casos de Borda e Erros
*(ajustar sempre à plataforma real do projeto — Web, Mobile, Desktop ou Microserviços/Cloud. Não reaproveitar exemplos de outro contexto sem checar se fazem sentido aqui.)*

- **Falhas de Conectividade / Rede:** <Timeouts, perda de sinal, degradação de latência>
- **Concorrência e Estado:** <Cliques duplos, race conditions, registros simultâneos no BD, invalidação de cache/sessão>
- **Entradas de Dados e Limites:** <Payloads grandes, caracteres especiais, rate-limit de API>
- **Segurança e Permissões:** <Sessão expirada, falta de autorização (401/403), CSRF — e, se houver mais de um papel de usuário, quais ações cada papel pode/não pode executar>
- **Recuperação e Idempotência:** <Comportamento do sistema ao reexecutar uma ação que falhou pela metade>

---

## 5. Proposta de ADR — Registro de Decisão Arquitetônica
*(preenchido pela IA, se aplicável)*

- **Título:** ADR-<XX>: <Nome da Decisão>
- **Contexto:** <Problema técnico resolvido>
- **Decisão:** <Padrão escolhido>
- **Consequências:** <Impactos positivos e negativos>

---

## 6. Funções de Aptidão (Fitness Functions) & Critérios de Aceite
*(preenchido pela IA)*

- [ ] **Coesão & Isolamento:** Testes unitários cobrem o novo módulo sem mocks complexos de UI.
- [ ] **Acoplamento Limpo:** Nenhuma violação de camadas nos imports.
- [ ] **Tratamento de Exceções:** Nenhuma exceção capturada em silêncio.
- [ ] **Contrato Tipado:** Interfaces expostas possuem tipagem declarada.
- [ ] **Sem Hardcode:** Nenhum valor que deveria vir de configuração ou versão está fixado manualmente no código.
