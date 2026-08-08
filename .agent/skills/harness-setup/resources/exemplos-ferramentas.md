# Exemplos de Ferramentas por Categoria (Referência, não Prescrição)

*(esta tabela é só ilustrativa — o cenário de ferramentas muda rápido. Ao montar o plano, confirme se o exemplo abaixo ainda é o recomendado para o stack real do projeto; pesquise na web se houver dúvida ou se o ecossistema do projeto não estiver listado aqui.)*

Cada linha é uma **categoria de sensor/guide**, não uma ferramenta obrigatória. O plano deve citar a categoria; o exemplo serve só pra dar chão de implementação.

| Categoria | JS/TS | Python | JVM (Java/Kotlin) | Go | Ruby |
|---|---|---|---|---|---|
| Linter | ESLint, Biome | Ruff, Pylint | Checkstyle, ktlint | golangci-lint | RuboCop |
| Type checking estrito | TypeScript `strict` | mypy, Pyright | (tipagem estática nativa) | (tipagem estática nativa) | Sorbet |
| Testes + coverage | Vitest/Jest + c8 | pytest + coverage.py | JUnit + JaCoCo | go test -cover | RSpec + SimpleCov |
| Mutation testing | Stryker | mutmut, cosmic-ray | PIT | go-mutesting | Mutant |
| Regras de dependência/acoplamento | dependency-cruiser | import-linter, grimp | ArchUnit | go-arch-lint | Packwerk |
| Dead code / unused exports | knip, ts-prune | vulture, deptry | (analisadores de IDE/build) | deadcode, unused | debride |
| Pre-commit hooks | husky + lint-staged | framework `pre-commit` | Git hooks nativos + Gradle/Maven plugin | Git hooks nativos + `golangci-lint run` | overcommit |
| SAST | Semgrep (multi-linguagem) | Semgrep, Bandit | Semgrep, SpotBugs | Semgrep, gosec | Semgrep, Brakeman |
| Dependency scan | Dependabot/Renovate (multi-linguagem) | pip-audit, Dependabot | Dependabot, OWASP Dependency-Check | govulncheck, Dependabot | bundler-audit |
| Fuzz testing | fast-check (property-based) | Hypothesis, Atheris | jqwik | go-fuzz (nativo desde 1.18) | Rantly |
| Logging estruturado | pino, winston | structlog | Logback + MDC | slog (nativo desde 1.21) | Lograge |

## Categorias sem exemplo fixo (variam demais por domínio/infra)
- Health check endpoint — depende do framework web usado
- Métricas de runtime / SLOs — depende da infra de observabilidade já adotada (Prometheus, Datadog, BetterStack, etc.)
- Tracing distribuído — depende de quantos serviços existem e da infra de observabilidade

## Como usar esta tabela no plano
Ao preencher `resources/harness-plano.md`, cite a categoria e o exemplo relevante ao stack real do projeto (lido de `fundacao.md`, Seção 6). Se o stack não aparecer nesta tabela, ou se você suspeitar que o ecossistema mudou desde a última atualização deste arquivo, pesquise na web pela ferramenta atualmente recomendada antes de propor algo no plano.
