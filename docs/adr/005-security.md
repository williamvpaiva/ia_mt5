 ADR 005 – Segurança
 Status: Proposto

 Contexto
 - Segurança é uma preocupação transversal: autenticação/autorização, validação de entradas, gestão de segredos, criptografia, e proteção de dados sensíveis.
 - Precisa definir padrões para frontend/backend, políticas de acesso, e gestão de credenciais/secretos.

 Opções consideradas
 1) OAuth2/OpenID Connect com JWT, rotação de tokens, refresh tokens, e roles/grupos com RBAC.
 2) JWTs oxigenados com claims de acesso, combinados com SSO corporativo.
 3) Secrets management com Vault/AWS Secrets Manager, com práticas de injeção segura de segredos em ambientes (CI/CD, containers).

 Decisão (proposta)
 - Adotar OAuth2/OIDC (issuer corporativo) para autenticação, com RBAC no backend e constraints de access at object level. Usar JWTs com rotação de tokens para chamadas entre serviços.
 - Garantir validação de entrada (sanitização e validação estrita) no backend e validação de dados no frontend antes de enviar ao servidor.
 - Gestão de segredos com Vault ou AWS Secrets Manager, com rotation periódica e políticas de acesso mínimo.
 - Criptografia em trânsito (TLS 1.2+) e criptografia em repouso conforme requisitos legais.

 Consequências
 - Maior segurança e conformidade com padrões comuns (HIPAA/GDPR/etc. conforme aplicação).
 - Maior complexidade inicial de configuração, porém com maior previsibilidade de segurança a longo prazo.
