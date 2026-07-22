# Guía paso a paso — Módulo 8 (Telemetría)

Guía pensada para ejecutar todo de cero, sin dar nada por supuesto. Si algo falla, cada bloque tiene su sección de "si algo va mal".

Los ejercicios 2, 3 y 4 son teóricos (están resueltos en `02-04-teoria.md`, no hay nada que ejecutar). Aquí se ejecutan el **Ejercicio 1**, el **Desafío 5.1** y el **Desafío 5.2**.

---

## Paso 0 — Requisitos previos (hazlo una sola vez)

### 0.1 Comprobar que tienes Docker

```bash
docker --version
docker compose version
```

Si ambos comandos devuelven una versión, salta al Paso 1.

Si `docker: command not found`, instala Docker Engine (en Ubuntu):

```bash
# Instalación oficial de Docker en Ubuntu
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 0.2 Poder usar Docker sin `sudo` (recomendado)

```bash
sudo usermod -aG docker $USER
```

Después de este comando **cierra la sesión y vuelve a entrar** (o reinicia), o el grupo no se aplica. Comprueba:

```bash
docker run --rm hello-world
```

Si ves un mensaje de "Hello from Docker!", ya está.

> Nota: como sysadmin acostumbrado a Podman rootless, aquí el daemon de Docker corre como root; añadirte al grupo `docker` es equivalente a darte acceso root a la máquina. En tu portátil de bootcamp es aceptable; tenlo en cuenta y no lo replicas en un servidor de verdad.

### 0.3 Descomprimir el material

```bash
tar -xzf modulo-08-telemetria.tar.gz
cd modulo-08-telemetria
```

Comprueba la estructura:

```bash
ls
# 01-prometheus-local  02-04-teoria.md  05-desafio-prometheus  05.2-desafio-jaeger  guia-pasos.md  README.md
```

---

## Paso 1 — Ejercicio 1: Prometheus en local scrapeándose a sí mismo

### 1.1 Ir a la carpeta y arrancar Prometheus

```bash
cd 01-prometheus-local
```

```bash
docker run -d \
  --name prometheus \
  -p 9090:9090 \
  -v "$(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml:ro" \
  prom/prometheus
```

Qué hace cada línea:
- `-d` → en segundo plano (detached), te devuelve la terminal.
- `--name prometheus` → nombre fijo para poder pararlo luego.
- `-p 9090:9090` → publica el puerto web por defecto de Prometheus. Izquierda = tu máquina, derecha = dentro del contenedor.
- `-v "$(pwd)/prometheus.yml:...:ro"` → mete tu fichero de configuración dentro del contenedor en modo solo lectura (`ro`).

### 1.2 Comprobar que arrancó

```bash
docker ps
```

Debe aparecer una línea con `prometheus` y estado `Up`. Si no aparece, mira los logs:

```bash
docker logs prometheus
```

### 1.3 Abrir la interfaz web

En el navegador: **http://localhost:9090**

Comprueba el auto-scraping en **Status → Target health** (menú de arriba). Debe salir el target `http://localhost:9090/metrics` en estado **UP** (verde).

Alternativa desde la propia consola: ve a la pestaña de queries, escribe `up` y pulsa **Execute**. Debe devolver `1`.

### 1.4 Las dos queries que pide el enunciado

Pega cada una en la caja de query y pulsa **Execute** (pestaña **Graph** para verlas dibujadas).

**Memoria utilizada:**
```promql
process_resident_memory_bytes{job="prometheus"}
```
Es la memoria RAM (residente, RSS) que consume el propio proceso de Prometheus, en bytes.

**CPU utilizada:**
```promql
rate(process_cpu_seconds_total{job="prometheus"}[1m])
```
`process_cpu_seconds_total` solo crece (es un *counter* de segundos de CPU). `rate(...[1m])` lo convierte en "CPU por segundo durante el último minuto": `0.02` ≈ 2% de un core.

### 1.5 Parar y limpiar

```bash
docker rm -f prometheus
```

```bash
cd ..
```

---

## Paso 2 — Desafío 5.1: docker compose con la app + Prometheus

Aquí levantamos dos cosas a la vez: la app `app_map` (ya instrumentada para exponer `/metrics/`) y un Prometheus que la scrapea.

### 2.1 Ir a la carpeta

```bash
cd 05-desafio-prometheus
```

Mira lo que hay:

```bash
ls
# app_map  docker-compose.yml  prometheus  README.md
```

### 2.2 Levantar todo

```bash
docker compose up -d --build
```

- `up` → arranca los servicios del `docker-compose.yml`.
- `-d` → en segundo plano.
- `--build` → construye la imagen de la app desde su `Dockerfile` (la primera vez es obligatorio; tarda un poco porque descarga Python e instala dependencias).

Cuando termine:

```bash
docker compose ps
```

Deben aparecer `app-map` y `prometheus`, ambos `running`/`Up`.

### 2.3 Comprobar la app directamente (antes de mirar Prometheus)

```bash
curl -s http://localhost:8000/api/items/
```
Debe devolver una lista JSON con Foo1, Foo2, Foo3.

```bash
curl -s http://localhost:8000/metrics/ | head
```
> **OJO A LA BARRA FINAL**: es `/metrics/` **con** barra. Sin barra (`/metrics`) devuelve 404. Esto no es un capricho: la app monta los ficheros estáticos en `/`, y esa ruta se traga cualquier petición que no coincida exactamente con otro mount. Ya lo comprobé con curl al montar el ejercicio.

Debe salir texto tipo `python_info{...} 1.0`, `process_resident_memory_bytes ...`, etc.

### 2.4 Verificar el target en Prometheus (esto es lo que pide el enunciado)

En el navegador: **http://localhost:9090** → **Status → Target health**.

Deben salir **dos** targets en **UP**:
- `prometheus` (él mismo).
- `app-map` → `http://app-map:8000/metrics/`.

> `app-map` es el nombre del servicio en el compose; dentro de la red de Docker, Prometheus lo resuelve por ese nombre. Por eso el `prometheus.yml` apunta a `app-map:8000` y no a `localhost`.

Confirmación por query — escribe en la caja y **Execute**:

```promql
up{job="app-map"}
```
Debe devolver `1`.

Y para ver que las métricas de la app realmente están llegando:

```promql
process_resident_memory_bytes{job="app-map"}
rate(process_cpu_seconds_total{job="app-map"}[1m])
```

### 2.5 Capturas recomendadas para la entrega

1. La pantalla **Target health** con los dos targets en UP.
2. La query `up` mostrando ambos jobs a `1`.

### 2.6 Parar y limpiar

```bash
docker compose down
```

```bash
cd ..
```

### Si algo va mal en 5.1

- **`app-map` sale DOWN en Prometheus** → casi seguro es la barra final. Confirma que `prometheus/prometheus.yml` tiene `metrics_path: /metrics/`. Mira también `docker compose logs app-map`.
- **Error al construir la imagen** con `uvicorn.workers` → si ves `ModuleNotFoundError: uvicorn.workers`, edita `app_map/Dockerfile`: cambia el `CMD` para usar `-k uvicorn_worker.UvicornWorker` y añade `uvicorn-worker` a `requirements.txt`. (Con las versiones actuales no debería pasar, pero queda anotado.)
- **Puerto 8000 o 9090 ocupado** → `sudo ss -ltnp | grep -E ':8000|:9090'` para ver quién lo usa; o cambia el puerto izquierdo en el `docker-compose.yml` (p. ej. `8001:8000`).

---

## Paso 3 — Desafío 5.2: Jaeger + HotROD

Este desafío es "sigue el tutorial y toma notas". El tutorial original es de 2017 y sus comandos ya no valen (HotROD ahora usa OpenTelemetry/OTLP), así que usamos el compose actualizado que está en la carpeta.

### 3.1 Ir a la carpeta y arrancar

```bash
cd 05.2-desafio-jaeger
docker compose up -d
```

```bash
docker compose ps
```
Deben salir `jaeger` y `hotrod`, ambos arriba.

### 3.2 Abrir las dos interfaces

- **HotROD** (la app de demo): http://localhost:8080
- **Jaeger** (donde se ven las trazas): http://localhost:16686

### 3.3 Generar tráfico

En la UI de HotROD, pulsa uno de los botones de cliente (p. ej. "Rachel's Floral Designs"). Cada clic simula pedir un coche. Pulsa varias veces seguidas y rápido para provocar contención (es lo interesante).

### 3.4 Ver la traza en Jaeger

En Jaeger UI:
1. **Service**: `frontend`.
2. **Operation**: `HTTP GET /dispatch`.
3. **Find Traces**.
4. Abre una traza. Verás el diagrama de Gantt con la cascada `frontend → customer → driver → route`.

### 3.5 Los dos "issues" que el tutorial te hace descubrir

- **Issue 1 (base de datos):** expande el span **`mysql SQL SELECT`** (no el de `customer`). En sus **logs (events)** aparece, cuando hay concurrencia, `Waiting for lock behind N transactions` y `Acquired lock; N transactions waiting behind`: la BD simulada tiene una sola conexión, así que con varias peticiones a la vez las queries se serializan. Necesitas clicar varios botones rápido para verlo; con un clic aislado el span dura solo ~300ms y no sale el log de "Waiting".
- **Issue 2 (route):** haz scroll hasta el bloque de 10 spans `route` (pasado el span `driver`). Mira dónde **empieza** cada barra: arrancan en tandas de 3 (3+3+3+1) porque hay un pool de 3 workers. Se ve como "escalones" en el Gantt.

### 3.6 Aplicar los fixes y comparar

Edita `docker-compose.yml` y cambia la línea `command` del servicio `hotrod` por:

```yaml
    command: ["all", "--fix-db-query-delay=100ms", "--fix-disable-db-conn-mutex", "--fix-route-worker-pool-size=100"]
```

Recrea solo ese contenedor:

```bash
docker compose up -d --force-recreate hotrod
```

Vuelve a generar tráfico (paso 3.3) y a mirar la traza (paso 3.4). La duración de `/dispatch` debería bajar mucho y desaparecer los escalones.

> Truco: Jaeger permite comparar dos trazas lado a lado (selecciona dos y usa "Compare"). Perfecto para documentar el antes/después.

### 3.7 Rellenar tus notas

Abre `README.md` de esta carpeta: al final tiene una plantilla de notas (setup, primera traza, diagnóstico del lock, worker pool, resultados tras los fixes, reflexión). Esa parte es tuya y es lo que se evalúa del desafío.

### 3.8 Parar y limpiar

```bash
docker compose down
cd ..
```

### Si algo va mal en 5.2

- **No aparecen trazas en Jaeger** → asegúrate de haber generado tráfico *después* de que ambos contenedores estén arriba. Revisa `docker compose logs hotrod`: debe estar exportando a `http://jaeger:4318`.
- **Puerto 8080 ocupado** (típico, lo usan muchas apps) → cambia `8080:8080` por `8090:8080` en el compose y entra por http://localhost:8090.

---

## Chuleta de comandos Docker (por si te pierdes)

```bash
docker ps                 # contenedores corriendo
docker ps -a              # todos, incluidos parados
docker logs <nombre>      # ver logs de un contenedor
docker compose logs -f    # logs de todos los servicios del compose, en vivo
docker compose ps         # estado de los servicios del compose
docker compose up -d      # arrancar en segundo plano
docker compose down       # parar y borrar los contenedores del compose
docker rm -f <nombre>     # matar y borrar un contenedor suelto
docker stats --no-stream  # uso de CPU/RAM de los contenedores (una foto)
```
