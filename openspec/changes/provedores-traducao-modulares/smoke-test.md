# Smoke test manual — Google Web (tarefa 9.2)

Executado fora do CI em 2026-08-06, sem credenciais e sem conteúdo de
livro (apenas a string de teste "Hello world").

## Variante validada

- `transport_variant = html-v1/text-v2`
- Perfil textual: `https://translate.googleapis.com/translate_a/single`
  com `client=gtx` (responde sem chave). A variante anterior `client=webapp`
  passou a responder HTTP 403 e foi substituída.
- User-Agent: `tradutor-ebook/experimental (EPUB translator)`.

## Resultados

| Verificação | Resultado |
| --- | --- |
| `test_connection` | OK via fallback textual (perfil HTML indisponível) |
| Tradução de texto puro ("Hello world" → pt-BR) | OK ("Olá mundo"), uso sem tokens/custo |
| Perfil HTML `translate-pa.googleapis.com/v1/translateHtml` | POST 403 ("unregistered callers" — exige API key); GET 404 |
| Blocos com markup inline | Falham com erro acionável (fallback textual recusado para preservar XHTML, conforme design) |

## Conclusão

O provider opera hoje pelo perfil textual para blocos de texto puro;
blocos com markup inline dependem do perfil HTML, que atualmente exige
chave (override operacional `public_key` existe para isso). O provider
permanece classificado como experimental/unofficial, e a UI já exibe os
avisos de instabilidade, limites e ausência de custo mensurável.
