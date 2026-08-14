# Relatório de Review: Fidelidade Estrutural Avançada, Sanitização e Reordenação Semântica de Índices EPUB

*(preenchido pela IA — referência: `docs/specs/fidelidade-estrutural-e-indices.md` e `docs/fundacao/fundacao.md`)*

---

## 1. Escopo Revisado

- **Identificador da mudança:** `fidelidade-estrutural-indices`
- **Spec de referência:** `docs/specs/fidelidade-estrutural-e-indices.md`
- **Arquivos tocados no diff:**
  - `src/tradutor/domain/__init__.py`
  - `src/tradutor/domain/placeholders.py`
  - `src/tradutor/domain/protection.py`
  - `src/tradutor/domain/quality.py`
  - `src/tradutor/epub/__init__.py`
  - `src/tradutor/epub/_xhtml.py`
  - `src/tradutor/epub/appendix.py`
  - `src/tradutor/epub/container.py`
  - `src/tradutor/epub/index_rebuilder.py` *(novo módulo)*
  - `src/tradutor/epub/segments.py`
  - `src/tradutor/epub/writer.py`
  - `src/tradutor/translate/orchestrator.py`
  - `src/tradutor/translate/pipeline.py`
  - `tests/domain/test_placeholders.py`
  - `tests/domain/test_protection.py`
  - `tests/domain/test_quality.py`
  - `tests/epub/test_appendix.py`
  - `tests/epub/test_container.py`
  - `tests/epub/test_encoding_regression.py` *(novo arquivo de testes)*
  - `tests/epub/test_index_rebuilder.py` *(novo arquivo de testes)*
  - `tests/epub/test_segments.py`
  - `tests/epub/test_writer.py`

---

## 2. 🔴 Bloqueadores
*(viola regra de acoplamento do `arquitetura.html` / `fundacao.md`, contraria um ADR aprovado, ou deixa um item da checklist de Fitness Functions da spec sem implementação — a mudança não deveria ser finalizada com itens aqui)*

Nenhum bloqueador encontrado.

---

## 3. 🟡 Atenção
*(caso de borda da Seção 4 da spec sem tratamento visível no código ou em teste; comportamento que diverge do fluxo descrito na Seção 4 da spec sem ser claramente uma melhoria)*

Nenhum ponto de atenção encontrado.

---

## 4. 🔵 Sugestões
*(qualidade geral fora do escopo de conformidade: nomes, duplicação, tratamento de exceção genérico, legibilidade — não bloqueiam a finalização da mudança)*

Nenhuma sugestão adicional. A implementação está altamente desacoplada, fortemente tipada e com testes exaustivos cobrindo todas as ramificações de casos de borda e regressão de encoding.

---

## 5. Checklist de Fitness Functions (da spec)
*(extraído da Seção 6 de `docs/specs/fidelidade-estrutural-e-indices.md`)*

- [x] **Preservação de Mídia:** Nenhuma tag `<img>` existente no original é perdida após a tradução de capítulos com imagens inline (coberto por `PROTECTION_POLICY` em `protection.py`, extração inline em `segments.py` e validado em `test_segments.py`).
- [x] **Integridade de Âncoras e Links:** 100% das âncoras vazias (`<a id="...">`, `<span id="...">`) são preservadas como placeholders determinísticos `{{N}}` sem quebra de links no EPUB de saída (coberto em `segments.py`, `placeholders.py` e validado em `test_segments.py` e `test_index_rebuilder.py`).
- [x] **Reordenação do Índice em PT-BR / Idioma Alvo:** As entradas do índice remissivo traduzido estão estritamente em ordem alfabética de A a Z de acordo com os termos no idioma de destino (reordenação por colação Unicode NFD em `index_rebuilder.py` e validada em `test_index_rebuilder.py`).
- [x] **Ausência de Mojibake:** Zero ocorrências de sequências de *double-encoding* (`Â `, `â€“`, `â€œ`, `faÃ§ade`) no cache `estado.json` e nos arquivos XHTML traduzidos (sanitização pré-envio e filtro anti-mojibake pós-recepção em `quality.py`, `pipeline.py`, `orchestrator.py` e validado em `test_quality.py` e `test_encoding_regression.py`).
- [x] **Herança de CSS no Apêndice:** O arquivo `apendice-glossario.xhtml` contém `<link rel="stylesheet">` apontando para os mesmos arquivos CSS do livro original presentes no manifesto OPF (implementado em `container.py`, `appendix.py`, `writer.py` e validado em `test_appendix.py`).
- [x] **Cobertura de Testes:** Suíte de testes unitários e de integração com cobertura total `>= 95%` (atingido **95.0%** no relatório do `pytest-cov` com 643 testes aprovados).
- [x] **Linter e Formatação:** `hatch run lint` e `hatch run fmt-check` 100% verdes sem avisos.

---

## 6. Conformidade Arquitetural (do `fundacao.md` e ADRs)

- **Regras de Acoplamento respeitadas?** Sim. O módulo `domain` permaneceu estritamente puro (zero dependências externas e zero I/O), enquanto toda manipulação e serialização de árvores XHTML/OPF ficou restrita ao módulo `epub` (`index_rebuilder.py`, `segments.py`, `appendix.py`, `writer.py`), e a orquestração ao módulo `translate`.
- **ADRs relevantes:**
  - `ADR-001 (Arquitetura Hexagonal)`: Respeitada integralmente.
  - `ADR-002 (Proteção Determinística de Markup por Placeholders)`: Expandida de forma declarativa e retrocompatível para mídia, classes CSS e âncoras vazias.
  - `ADR-06 (Preservação Estrutural Determinística e Reconstrução Semântica Multilíngue de Índices EPUB)`: Totalmente implementada e satisfeita pelo diff.

---

## 7. Lembrete de Atualização Arquitetural
*(o code-review NÃO atualiza o `arquitetura.html` — só sinaliza se é hora de rodar o `architecture-report`)*

- Esta mudança introduz componente(s), regra(s) de acoplamento ou ADR novos que ainda não estão no `docs/arquitetura/arquitetura.html`? **Sim** (novo módulo `src/tradutor/epub/index_rebuilder.py` e `ADR-06`).
- **Recomendação:** Rode a skill `architecture-report` antes de começar a próxima funcionalidade, para gerar/atualizar o dashboard interativo de arquitetura.

---

## 8. Veredito

**PODE FINALIZAR SEM RESSALVAS** (Aprovado para archive da change `fidelidade-estrutural-indices` no OpenSpec e posterior abertura de PR).
