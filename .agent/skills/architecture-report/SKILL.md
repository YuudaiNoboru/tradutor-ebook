---
name: architecture-report
description: Gera ou atualiza um painel interativo (HTML) contendo a análise arquitetônica do projeto, baseada nos conceitos do livro Fundamentos da Arquitetura de Software de Mark Richards e Neal Ford. Utiliza a abordagem Ator/Ação, mapeamento físico/lógico, métricas de acoplamento, coesão, trade-offs e registros de decisões de design (ADRs).
---

# Skill: Análise de Arquitetura & Relatório Dinâmico (Richards & Ford)

Esta skill mapeia e documenta a arquitetura do projeto atual usando os conceitos de **Fundamentos da Arquitetura de Software** (Mark Richards e Neal Ford), organizando-os em um painel interativo em HTML.

Os arquivos de referência ficam em `resources/` **dentro desta skill** (caminho relativo, nunca absoluto): `resources/template.html`, `resources/style.css`, `resources/script.js`.

---

## 🎯 Objetivos da Skill

1. **Identificar Atores & Ações:** mapear os atores do sistema — incluindo **múltiplos papéis de usuário nomeados** quando existirem (ex: Comprador, Estoquista, Gerente — nunca assumir um único "Usuário" genérico), além de Sistema e Desenvolvedor — e suas ações, extraindo responsabilidades e acoplamentos.
2. **Definir Estruturas Lógica e Física:** mapear a arquitetura em camadas e associar a estrutura de diretórios aos componentes lógicos (Package-by-Component).
3. **Mapear Acoplamento & Coesão:** avaliar dependências e o tipo de coesão (Sequencial, Funcional, Lógica, etc.) de cada módulo.
4. **Registrar ADRs:** formalizar decisões cruciais de design.
5. **Avaliar Trade-offs:** montar a matriz de compromissos arquitetônicos.
6. **Gerar Artefatos:** escrever ou atualizar `arquitetura.html` na raiz do projeto (mais `arquitetura.css` e `arquitetura.js` na primeira execução).

---

## 🔄 Fluxo de Execução

### Passo 1: Preparação dos Artefatos Estáticos (uma única vez por projeto)
* Na raiz do projeto, verifique se `arquitetura.css` e `arquitetura.js` já existem.
  * **Se não existirem:** copie `resources/style.css` → `<RAIZ_DO_PROJETO>/arquitetura.css` e `resources/script.js` → `<RAIZ_DO_PROJETO>/arquitetura.js`, sem alterar o conteúdo.
  * **Se já existirem:** não sobrescreva — eles não mudam entre execuções, só o HTML de conteúdo muda. Isso evita reescrever ~2000 linhas de CSS/JS idênticas a cada rodada.
* Verifique se `arquitetura.html` já existe:
  * **Se existir:** leia-o e extraia os atores, componentes, ADRs e trade-offs já documentados — a atualização deve preservar decisões existentes que ainda são válidas, não recomeçar do zero.
  * **Se não existir:** carregue `resources/template.html` como ponto de partida.

### Passo 2: Levantar Atores & Ações (Achatamento Rígido)
* Identifique todos os papéis de usuário distintos do projeto (nunca um "Usuário" genérico único, salvo se o projeto realmente só tiver um tipo de usuário) mais Sistema e Desenvolvedor.
* Monte uma tabela achatada, uma linha por ação:
  `Ator | Ação | Componente Lógico/Físico | Requisito/Spec | Funções e Responsabilidades | Características Arquitetônicas | Acoplamento`
* Não mescle células — isso quebra os filtros e a busca em tempo real do painel.
* Cada papel de usuário recebe um slug (ex: `comprador`, `estoquista`) usado consistentemente em `data-actor-type` (linhas da tabela), `data-actor` (botões de filtro) e nos ids do diagrama (`path-<slug>`, `info-<slug>`) — ver comentários em `resources/template.html` e `resources/script.js`.

### Passo 3: Mapear Classes, Funções e Ficheiros
* Para cada pasta física de código, mapeie o arquivo correspondente e liste métodos/classes centrais.
* Use caminhos **relativos à raiz do projeto** (ex: `src/tradutor/tui/app.py`), nunca caminhos absolutos de uma máquina específica — isso garante que o painel funcione em qualquer clone/checkout do repositório.

### Passo 4: Desenhar Diagramas em SVG
* Diagramas inline em SVG para:
  1. **Figura 1 — Atores & Ações:** fluxo de cliques por ator (um clique por slug de ator, incluindo todos os papéis de usuário identificados no Passo 2).
  2. **Figura 2 — Estrutura Lógica:** camadas (Apresentação, Domínio/Orquestração, Infraestrutura/Adapters).
  3. **Figura 3 — Estrutura Física:** ligação de pastas aos componentes.
  4. **Figura 4 — Acoplamento por Processo:** seletor interativo entre os principais processos do sistema, destacando em vermelho as vias de acoplamento reduzido/isolado.

### Passo 5: Gerar / Atualizar ADRs e Trade-offs
* Para cada ADR: Título, Status (Aprovada/Proposta), Contexto, Decisão, Consequências (positivas e negativas).
* Matriz de trade-offs (escala 1–5): Deployability, Simplicity, Testability, Scalability, Security, Extensibility.

### Passo 6: Revisão & Aprovação (antes de gravar)
* Apresente ao desenvolvedor um resumo do que vai mudar em relação à versão anterior do `arquitetura.html` (se existia): novos/removidos atores, ADRs novos ou alterados, mudanças na matriz de trade-offs.
* Só grave o arquivo depois da confirmação do desenvolvedor. Não sobrescreva `arquitetura.html` silenciosamente — ADRs e trade-offs são registros de decisão, não devem ser alterados sem revisão humana.

### Passo 7: Gravação do Artefato
* Substitua apenas o conteúdo de `<div class="main-content">` no HTML (os `tab-pane` de cada seção) e salve como `arquitetura.html` na raiz do projeto.
* Não toque em `arquitetura.css` nem `arquitetura.js` neste passo — eles já foram tratados no Passo 1.

---

## 🛠️ Diretrizes e Regras de Qualidade
* **Sem caminhos hardcoded:** nada nesta skill ou no HTML gerado deve referenciar um caminho absoluto de uma máquina específica (ex: `C:\Users\<nome>\...`). Tudo relativo à raiz do projeto.
* **Preservação de Estilo:** layout de Sidebar Navegável e Recolhível, com suporte responsivo mobile — definido em `arquitetura.css`, não duplicado no HTML.
* **Nomes dos Arquivos:** `arquitetura.html`, `arquitetura.css`, `arquitetura.js`, sempre na raiz do projeto.
* **Atores dinâmicos:** o número de papéis de usuário não é fixo em 3 — cresce ou diminui conforme o projeto real. Sistema e Desenvolvedor são sempre fixos; os demais são descobertos no Passo 2.
* **Sem placeholders vazios:** se o projeto não usa certo recurso (ex: keyring do SO), documente isso como trade-off explícito em vez de deixar campo em branco.
