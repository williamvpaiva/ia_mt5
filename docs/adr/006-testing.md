 ADR 006 – Estratégia de Testes
 Status: Proposto

 Contexto
 - Garantir qualidade através de testes abrangentes em frontend e backend (unitário, integração, E2E, performance, segurança).
 - Precisamos definir a estratégia de teste para cada camada e como eles serão integrados no CI/CD.

 Opções consideradas
 1) Testes unitários e de integração amplos no backend (NestJS/Express) com Jest. E2E com Playwright para fluxos críticos.
 2) Testes end-to-end adicionais com Cypress para fluxo de UI complexos.
 3) Testes de performance/ carga com k6 para APIs críticas.
 4) Testes de segurança estática (SAST) e dinâmica (DAST) em pipelines de CI.

 Decisão (proposta)
 - Backend: Jest para unitários e testes de integração; validação baseada em contrato com OpenAPI; testes de ponta a ponta com Playwright para cenários críticos.
 - Frontend: Jest + React Testing Library para componentes; End-to-End com Playwright; validação de acessibilidade nos testes automatizados.
 - Performance: incluir testes de carga com k6 para endpoints críticos; budget de performance e monitoramento de SLIs.
 - Segurança: incorporar SAST/DAST no pipeline de CI; verificação de dependências vulneráveis com análise SBOM.

 Consequências
 - Alta qualidade com feedback rápido; detecção precoce de regressões.
 - Maior tempo de pipeline, mas com menor risco de falhas em produção.
