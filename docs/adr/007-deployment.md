 ADR 007 – Deployment e Entrega
 Status: Proposto

 Contexto
 - Necessidade de padrões consistentes de deployment, pipelines CI/CD, ambientes (dev/stage/prod), observabilidade em produção e estratégias de rollback.

 Opções consideradas
 1) CI/CD com GitHub Actions, deploy para cloud (AWS/Azure/GCP) com infraestrutura como código (Terraform/CDK) e rollouts controlados.
 2) GitOps com ArgoCD/Flux para Kubernetes com ambientes imutáveis e observabilidade integrada.
 3) Deploys serverless com pipelines simples usando Lambdas/Layers (ou funções) com etapas de promoção entre ambientes.

 Decisão (proposta)
 - Adotar CI/CD com GitHub Actions + Terraform para provisionamento e gestão de infra. Deploy para Kubernetes (GKE/AKS/EKS) com ArgoCD para GitOps, se a seção de infraestrutura usar Kubernetes. Em ambientes serverless, usar pipelines dedicados com monitoramento de custos e performance.
 - Definir políticas de rollout (blue/green ou canary) para releases críticas; automatizar rollback em caso de falha crítica.
 - Integrar observabilidade (logs, métricas, tracing) desde o deploy, com dashboards de produção.

 Consequências
 - Deploys mais previsíveis, com capacidade de rollback rápido.
 - Maior governança de infra e custo, melhor rastreabilidade de mudanças.
