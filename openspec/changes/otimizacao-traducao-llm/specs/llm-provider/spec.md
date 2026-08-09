## MODIFIED Requirements

### Requirement: Retry com backoff
O sistema SHALL repetir chamadas HTTP que falham por erro transitório (429, 5xx, timeout) com até 3 tentativas (`max_retries = 3`), timeout de 45 segundos por chamada e tempo máximo de espera de 15 segundos entre tentativas (`max_delay = 15.0`), e SHALL reportar falha após esgotar as tentativas.

#### Scenario: Erro transitório recuperável
- **WHEN** uma chamada falha com 429 ou 5xx
- **THEN** o sistema tenta novamente com no máximo 15s de espera e conclui a tradução quando a API responde

#### Scenario: Falha definitiva
- **WHEN** as 3 tentativas se esgotam ou ocorre timeout de 45s
- **THEN** o bloco é marcado como pendente de retomada e a execução continua nos demais blocos sem interromper o livro inteiro
