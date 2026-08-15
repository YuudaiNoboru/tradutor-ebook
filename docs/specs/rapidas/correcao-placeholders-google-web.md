# Modificação Rápida: Preservação de Placeholders e Tolerância Estrutural no Google Web

*(preenchido em conjunto por desenvolvedor e IA — sem debate de trade-offs, sem ADR)*

## O que muda

1. **Proteção de Placeholders no Endpoint HTML (`/translateHtml`)**:
   - Em `src/tradutor/providers/machine_translation/google_web.py`, envelopar todos os placeholders `{{N}}` em nós `<span class="notranslate">{{N}}</span>` (ou `translate="no"`) antes de enviar o payload ao endpoint HTML.
   - O Google Translate respeita nativamente tags com classe `notranslate` e atributo `translate="no"`, preservando o nó DOM intacto na tradução sem descartar nem corromper seu conteúdo interno.
   - Ao receber a resposta, remover a tag envolvente `<span>`, restaurando os placeholders `{{N}}` originais de forma determinística.

2. **Normalização e Descolamento de Placeholders em Palavras (`extract_protected`)**:
   - Em `src/tradutor/domain/placeholders.py`, garantir que placeholders embutidos sem espaço adjacente a caracteres alfanuméricos (`word{{0}}` ou `{{0}}word`) sejam separados com espaço durante a extração de conteúdo protegido, estendendo a lógica de `normalize_hyphenated_placeholders`.
   - Isso impede que o motor neural de tradução veja o placeholder como parte integrante de um vocábulo ou expressão idiomática (ex.: `flying by the {{0}}seat of their pants` -> `flying by the {{0}} seat of their pants`).

3. **Proteção no Fallback Textual e Limpeza**:
   - No fallback textual do `GoogleWebProvider`, garantir que placeholders `{{N}}` também sejam mascarados com tokens `@@N@@` antes do envio a `/translate_a/t` e desmascarados por `unmask_markup`.
   - Ajustar `clean_placeholders` para tolerar variações de chaves com espaçamentos múltiplos (ex.: `{ { 0 } }` ou `@ @ 0 @ @`).
   - Evitar que uma falha de fidelidade de formatação pontual em um bloco desative permanentemente o endpoint HTML para todo o resto do livro.

4. **Testes Unitários e de Regressão**:
   - Testes unitários para `GoogleWebProvider` verificando tradução HTML com placeholders em expressões idiomáticas e sem perda de tokens.
   - Testes de extração em `test_placeholders.py` verificando descolamento de placeholders colados em palavras.
   - Testes do fallback textual com múltiplos placeholders e tags.

## Por que

- Durante a tradução de `ddd.epub` usando o provedor Google Web (experimental), a tradução quebrou com `GoogleWebResponseError: resposta alterou placeholder do bloco 280`.
- O bloco 280 em `OEBPS/html/pref03.html` continha uma âncora posicional vazia `<a id="page_xx"></a>` imediatamente colada ao termo `seat` (`flying by the <a id="page_xx"></a>seat of their pants`).
- O placeholder gerado `{{0}}seat` foi interpretado como texto comum pelo endpoint HTML do Google e descartado ao traduzir a expressão idiomática ("flying by the seat of their pants" $\to$ "estavam improvisando").
- O fallback textual subsequente também perdeu o placeholder por ausência de mascaramento, resultando em falha definitiva e abortando a tradução.

## Arquivos afetados

- `src/tradutor/domain/placeholders.py` — normalização de placeholders colados a palavras e limpeza tolerante de chaves.
- `src/tradutor/providers/machine_translation/google_web.py` — envelopamento de placeholders com `<span class="notranslate">`, mascaramento no fallback textual e isolamento de fallback por lote.
- `tests/domain/test_placeholders.py` — testes unitários para descolamento de placeholders colados e limpeza.
- `tests/providers/test_google_web.py` — testes de tradução com placeholders em HTML e no fallback textual.

## Risco de Regressão

**Baixo** — Trata-se de aperfeiçoamento da camada de proteção de marcação do Google Web e normalização de templates de placeholders na extração, mantendo total compatibilidade com `restore_protected` e os demais provedores.

## Precisa de teste novo?

**Sim**:
- Teste de `extract_protected` com placeholders colados a palavras (`the {{0}}seat` e `word{{0}}`) garantindo template higienizado e restauração correta.
- Testes no `test_google_web.py` simulando respostas HTML e textuais com placeholders protegidos.
- Teste real com o bloco 280 de `ddd.epub`.

---

## ⚠️ Trava de Escalonamento

- Introduz um Ator/papel de usuário novo? **não**
- Cria ou muda uma regra de acoplamento entre componentes já registrada no `docs/arquitetura/arquitetura.html`? **não**
- Contraria ou exige revisar um ADR aprovado? **não**
- Muda comportamento observável de forma que mereça uma decisão arquitetural registrada? **não**

---

## 📌 Reconciliação Pós-Implementação

- **Status da Implementação:** Concluída com 100% de conformidade.
- **Implementações Realizadas:**
  1. `_protect_html_placeholders` e `_unprotect_html_placeholders` adicionados em `src/tradutor/providers/machine_translation/google_web.py` para envelopar `{{N}}` em `<span class="notranslate">{{N}}</span>` (ou `translate="no"`) e restaurá-los de volta após o parsing de resposta HTML.
  2. `_translate_group` aprimorado para isolar falhas de formatação HTML pontuais sem desativar o endpoint HTML globalmente para lotes futuros do livro.
  3. `clean_placeholders` em `src/tradutor/domain/placeholders.py` atualizado com suporte a variações de espaços múltiplos aninhados em chaves e marcadores.
  4. Testes unitários adicionados em `tests/domain/test_placeholders.py` e `tests/providers/test_google_web.py`.
- **Validação Final:** 663 testes aprovados no `pytest`, 0 erros no lint (`hatch run lint`), formatação checada (`hatch run fmt-check`) e cobertura de 95% (`hatch run cov`).
