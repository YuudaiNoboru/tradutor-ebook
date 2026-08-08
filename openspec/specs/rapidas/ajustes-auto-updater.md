# Modificação Rápida: Ajustes no Auto-Updater

*(preenchido em conjunto por desenvolvedor e IA — sem debate de trade-offs, sem ADR)*

## O que muda
Implementação de correções e melhorias no auto-atualizador:
1. Validação de ambiente através de `is_frozen_windows()` ao reiniciar/aplicar a atualização no botão "Reiniciar" (`restart-btn`) da tela de update.
2. Impedir verificação manual de atualizações fora do ambiente executável compilado Windows na tela de configuração.
3. Ocultar componentes de atualização automática (checkbox `auto-check` e botão `check-now`) na tela de configuração em sistemas que não sejam Windows.
4. Propagar erros de rede/conexão na busca manual sob demanda de atualizações para evitar falso feedback.
5. Alterar o timeout do `httpx.Client` de download de 30s globais para um timeout resiliente `httpx.Timeout(30.0, read=10.0)`.

## Por que
Evitar que usuários em ambiente de desenvolvimento (mesmo no Windows) ou em sistemas operacionais não suportados executem o script de substituição destrutivo, corrompendo o interpretador de Python local; ocultar componentes irrelevantes em outras plataformas; e fornecer informações de falha realistas ao usuário.

## Arquivos afetados
- `src/tradutor/infra/updater.py`
- `src/tradutor/tui/screens/update.py`
- `src/tradutor/tui/screens/config.py`

## Risco de Regressão
Baixo — as alterações apenas adicionam validações de sistema operacional e de ambiente frozen, além de ajustar timeouts e propagação de erros, mantendo o fluxo existente inalterado para o usuário final no Windows compilado.

## Precisa de teste novo?
Sim, os testes unitários e de integração existentes serão atualizados para cobrir as novas proteções e o comportamento do auto-atualizador.

---

## ⚠️ Trava de Escalonamento
*(a IA preenche isto antes de finalizar — se qualquer resposta for "sim", PARE e sugira migrar para o fluxo completo de `especificar-funcionalidade`, com debate e modelo.md)*

- Introduz um Ator/papel de usuário novo? não
- Cria ou muda uma regra de acoplamento entre componentes já registrada no `arquitetura.html`? não
- Contraria ou exige revisar um ADR aprovado? não
- Muda comportamento observável de forma que mereça uma decisão arquitetural registrada? não
