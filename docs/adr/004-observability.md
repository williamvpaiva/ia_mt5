 ADR 004 – Observabilidade
 Status: Proposto

 Contexto
 - É necessário coletar métricas, logs e traces para diagnóstico, desempenho, confiabilidade e capacity planning.
 - Definir stack de observabilidade apropriada para frontend e backend.

 Opções consideradas
 1) Grafana/Prometheus para métricas, Loki para logs, Tempo/Jaeger para traces, com dashboards unificados.
 2) OpenTelemetry como padrão convergente para instrumentação em frontend e backend, com exportadores para tempo real.
 3) Soluções gerenciadas (New Relic, Datadog) caso o time tenha recursos para gerenciamento simplificado.

 Decisão (proposta)
 - Adotar OpenTelemetry como padrão de instrumentação, exportando para Tempo (tempo/opentelemetry-collector) e Grafana para dashboards. Usar Prometheus/Loki para métricas/logs conforme necessidade.
 - Implementar SLOs simples (ex.: latência de API, disponibilidade de endpoints críticos) e alertas básicos (PagerDuty/Alertmanager ou solução equivalente).
 - Instrumentar frontend (tempo de TTFB, LCP, CLS) e backend (latência de endpoints, taxa de erro, p95/99 de tempo de resposta).

 Consequências
 - Visibilidade clara de performance e confiabilidade; easier troubleshooting.
 - Capacidade de detecção proativa de problemas e melhoria orientada a dados.
