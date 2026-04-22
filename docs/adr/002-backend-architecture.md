 ADR 002 – Arquitetura de backend
 Status: Proposto

 Contexto
 - O backend precisa suportar APIs estáveis, segurança, escalabilidade, observabilidade, e integração com bancos de dados/serviços externos.
 - A stack atual não está definida de forma firme (pode ser Node.js, NestJS, ou outro). Este ADR delineia padrões a adotar.

 Opções consideradas
 1) Monolito modular com NestJS (+ Prisma) para API, ORM, validação e DI.
 2) Microserviços com NestJS ou Express + gRPC/REST entre serviços, com uma orquestração (Tempo, Temporal ou similar).
 3) Serviço/backend serverless com funções (Azure Functions/AWS Lambda) para endpoints sincronos simples, com filas para operações assíncronas.

 Decisão (proposta)
 - Adotar arquitetura de microserviços moderados (ou modular monolito com boundaries bem definidas) dependendo do tamanho do time e do domínio. Inicialmente: API RESTful com NestJS (ou equivalente) + Prisma para acesso a Postgres. Separar serviços por domínio (core, autenticação, dashboards, notificação) com limites de comunicação bem definidos.
 - Construir uma camada de APIs com OpenAPI, DTOs e validação (class-validator / zod) para garantir contratos consistentes.
 - Adoção de eventos para integrações assíncronas (event bus/Message broker) quando apropriado, com suporte a eventual consistency.

 Consequências
 - Maior escalabilidade e isolamento de falhas.
 - Maior consistência entre frontend e backend via contratos de API.
 - Necessidade de governança de eventos, versionamento de APIs e estratégias de migração.
