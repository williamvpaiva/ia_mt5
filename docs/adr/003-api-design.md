 ADR 003 – Design de API
 Status: Proposto

 Contexto
 - O projeto precisa definir como expor funcionalidades (REST, GraphQL ou tRPC), versionamento, formatos e contratos.
 - Importante considerar ergonomia para frontend, evolução de domínio e governança de mudanças.

 Opções consideradas
 1) REST puro com OpenAPI 3.1, versionamento por URL, e DTOs bem definidas.
 2) GraphQL para consultas ricas, com gateway/federation conforme necessidade de multi- serviço.
 3) gRPC entre serviços com REST/GraphQL na camada pública.

 Decisão (proposta)
 - Iniciar com REST puro (OpenAPI 3.1) para contratos estáveis, documentação automática e fácil evoluções de API. Introduzir GraphQL ou gRPC apenas se houver necessidade de consultas muito complexas ou comunicação entre serviços de alto desempenho.
 - Use DTOs/Serialização consistente; validação de entrada robusta; padronizar mensagens de erro.
 - Versionamento de API via path (v1, v2) e possibilidade de versionamento por header.

 Consequências
 - Contratos de API estáveis e documentação clara.
 - Facilidade de evolução incremental da API sem rupturas de clientes.
 - Adoção futura de GraphQL ou gRPC conforme evolução de requisitos.
