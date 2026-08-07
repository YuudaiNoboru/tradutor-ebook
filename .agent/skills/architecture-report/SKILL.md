---
name: architecture-report
description: Gera ou atualiza um painel interativo (HTML) contendo a análise arquitetônica do projeto, baseada nos conceitos do livro Fundamentos da Arquitetura de Software de Mark Richards e Neal Ford. Utiliza a abordagem Ator/Ação, mapeamento físico/lógico, métricas de acoplamento, coesão, trade-offs e registros de decisões de design (ADRs).
---

# Skill: Análise de Arquitetura & Relatório Dinâmico (Richards & Ford)

Esta skill permite ao agente de IA mapear e documentar sistematicamente a arquitetura de qualquer projeto usando os conceitos de **Fundamentos da Arquitetura de Software** (de Mark Richards e Neal Ford), organizando-os em um painel interativo completo em HTML.

---

## 🎯 Objetivos da Skill

1. **Identificar Atores & Ações:** Mapear todos os atores (Usuários, Sistema, Desenvolvedores) e suas ações de forma a extrair as responsabilidades e acoplamentos.
2. **Definir Estruturas Lógica e Física:** Mapear a arquitetura em camadas e associar a estrutura de diretórios aos limites dos componentes lógicos (Package-by-Component).
3. **Mapear Acoplamento & Coesão:** Avaliar as dependências e o tipo de coesão (Sequencial, Funcional, Lógica, etc.) de cada módulo.
4. **Registrar ADRs (Architecture Decision Records):** Formalizar decisões cruciais de design tomadas no código-fonte.
5. **Avaliar Trade-offs:** Desenhar a matriz de compromissos arquitetônicos.
6. **Gerar Artefatos:** Escrever ou atualizar `arquitetura.html` na raiz do projeto.

---

## 🔄 Fluxo de Execução

### Passo 1: Varredura de Código & Preparações
* Faça uma busca recursiva no diretório do projeto (ou utilize o CodeGraph se houver o diretório `.codegraph/`) para entender o ecossistema, arquivos, classes e principais métodos.
* Verifique se já existe o arquivo `arquitetura.html` na raiz do workspace:
  * **Se existir:** Leia-o e extraia a estrutura atualizada de componentes e as decisões já documentadas.
  * **Se não existir:** Carregue o template de referência localizado nos recursos desta skill: `C:\Users\vasco\Software\tradutor-ebook\.agent\skills\architecture-report\resources\template.html`.

### Passo 2: Executar Análise Ator/Ação (Achatamento Rígido)
* Monte uma tabela achatada mapeando individualmente as ações por Ator.
* **Linhas Individuais:** Cada linha da tabela deve representar um mapeamento direto de:
  `Ator | Ação | Componente Lógico/Físico | Requisito/Spec | Funções e Responsabilidades | Características Arquitetônicas | Acoplamento`
* Não mescle células na tabela HTML para garantir a funcionalidade de filtros e busca em tempo real do painel.

### Passo 3: Mapear Classes, Funções e Ficheiros
* Para cada pasta física de código, mapeie o arquivo correspondente e liste os métodos/classes centrais que implementam a responsabilidade listada no Passo 2.
* Use links relativos de arquivo no formato `file:///` para que o usuário possa clicar na interface e abrir o código-fonte correspondente.

### Passo 4: Desenhar Diagramas em SVG
* A skill exige diagramas dinâmicos inline em SVG para:
  1. **Figura 1: Mapeamento de Atores:** Um fluxo de cliques mostrando qual ator dispara quais ações para quais componentes.
  2. **Figura 2: Estrutura Lógica:** Fluxo de camadas (Apresentação, Domínio/Orquestração, Infraestrutura/Adapters).
  3. **Figura 3: Estrutura Física:** Ligação física de pastas aos componentes do sistema.
  4. **Figura 4: Diagrama de Acoplamento por Processos (Interativo):** Um seletor onde o usuário pode alternar entre os principais processos do sistema para ver quais linhas e setas de acoplamento e injeção estão ativas, destacando em vermelho as vias onde o acoplamento é reduzido ou isolado.

### Passo 5: Gerar / Atualizar ADRs e Trade-offs
* Identifique e adicione registros formais de design (ADRs):
  * **Status:** Aprovada, Proposta, etc.
  * **Contexto:** Qual o problema enfrentado no código.
  * **Decisão:** Como a estrutura contornou o problema.
  * **Consequências:** Pontos positivos e negativos da decisão.
* Monte a matriz de trade-offs arquitetônicos (com escala de 1 a 5) comparando características críticas como: *Deployability, Simplicity, Testability, Scalability, Security, Extensibility*.

### Passo 6: Injeção de Dados e Gravação dos Artefatos
* **HTML:** Substitua as marcações e injete os dados consolidados no `arquitetura.html` salvando na raiz do projeto. Garanta que o menu lateral responsivo e recolhível funcione perfeitamente.

---

## 🛠️ Diretrizes e Regras de Qualidade
* **Preservação de Estilo:** O HTML deve utilizar o layout de **Sidebar Navegável e Recolhível** (com suporte responsivo mobile).
* **Nomes dos Arquivos:**
  * O painel HTML do workspace deve ser salvo estritamente como `arquitetura.html`.
* **Sem placeholders vazios:** Caso o projeto não utilize certos recursos (como chaveiros do SO), documente isso explicitamente como um trade-off em vez de deixar campos em branco.

