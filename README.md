# Bootcamp DevOps Lemoncode — Módulo 8: Telemetría

Entrega del módulo de telemetría (Prometheus, Loki y Jaeger).

## Estructura

- `01-prometheus-local/` — **Ejercicio 1**: Prometheus en Docker scrapeándose a sí mismo, con las queries de memoria y CPU.
- `02-04-teoria.md` — **Ejercicios 2, 3 y 4**: exporters / recording rules / alert rules, explicación de la carpeta `01-start-up-loki`, y estructura de una traza en Jaeger.
- `05-desafio-prometheus/` — **Desafío 5.1**: docker compose con la app `app_map` instrumentada con `prometheus-client` (FastAPI + Gunicorn) y Prometheus scrapeándola.
- `05.2-desafio-jaeger/` — **Desafío 5.2**: setup de HotROD + Jaeger, diagnóstico de los dos issues (lock de BD y worker pool) y notas de la experiencia.
- `capturas/` — capturas de pantalla referenciadas desde los README de cada ejercicio.

## Cómo ejecutar

Cada ejercicio tiene su propio README con los comandos. 
