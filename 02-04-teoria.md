# Ejercicios 2, 3 y 4 — Teoría

## Ejercicio 2 — Exporters, recording rules y alert rules

### Exporters

Lo primero que aprendí al montar Prometheus es que él no "entra" a mirar un servidor. Lo único que hace es lanzar peticiones HTTP al endpoint `/metrics` y esperar que allí haya métricas en formato Prometheus.

El problema es que prácticamente ningún servicio las expone así de serie.

Por ejemplo, un Linux no tiene un `/metrics`, PostgreSQL tampoco, NGINX tampoco. Para eso están los exporters.

En las prácticas he utilizado sobre todo `node_exporter`. Lo arrancas junto a la máquina que quieres monitorizar y él se dedica a leer `/proc`, `/sys` y el resto de información del sistema para convertirla en métricas de Prometheus. Al final Prometheus sólo ve un endpoint HTTP normal, aunque por debajo el exporter esté leyendo un montón de sitios distintos.

Con otros servicios funciona igual. PostgreSQL tiene `postgres_exporter`, NGINX tiene el suyo, MySQL también, y para comprobar servicios desde fuera está `blackbox_exporter`, que en lugar de leer métricas internas hace peticiones HTTP, TCP o ICMP y genera métricas a partir de la respuesta.

Cuando la aplicación es propia ya no hace falta ningún exporter. En ese caso se instrumenta directamente el código con una librería de Prometheus. En el laboratorio de Python, por ejemplo, utilicé `prometheus_client`, añadí las métricas por defecto y la propia aplicación empezó a publicar `/metrics` sin ningún componente intermedio.

### Recording rules

Al principio hice varias consultas PromQL bastante pesadas desde Grafana y enseguida se nota que, si el dashboard refresca continuamente, Prometheus recalcula la misma expresión una y otra vez.

Las recording rules sirven precisamente para evitar eso.

Se define una expresión PromQL y Prometheus la ejecuta automáticamente cada cierto intervalo. En lugar de devolver el resultado únicamente cuando alguien hace la consulta, lo guarda como una métrica nueva.

Así, en vez de que Grafana tenga que recalcular continuamente algo como:

```promql
sum(rate(http_requests_total[5m])) by (service)
```

consulta directamente la métrica ya calculada.

En los ejemplos suelen nombrarse con dos puntos (`service:http_requests:rate5m`) para distinguirlas de las métricas originales, aunque realmente el nombre puede ser cualquiera. Las reglas se guardan en ficheros YAML agrupadas por bloques, y cada grupo puede tener su propio intervalo de evaluación.

En laboratorios pequeños probablemente no se nota la diferencia, pero cuando hay miles de series sí evita bastante trabajo innecesario.

### Alert rules

Las alert rules se escriben prácticamente igual que las recording rules porque también son expresiones PromQL evaluadas periódicamente.

La diferencia es que aquí no se guarda una métrica nueva, sino que se comprueba si una condición se está cumpliendo.

Lo que más utilicé fue el campo `for`, porque evita falsas alarmas. Si una CPU sube al 100 % durante dos o tres segundos normalmente no interesa recibir un aviso. Con `for: 5m`, por ejemplo, la condición tiene que mantenerse cinco minutos antes de que la alerta pase realmente a estado Firing.

Mientras tanto permanece en estado Pending.

Además de la expresión (`expr`) suelen añadirse `labels`, para clasificar la alerta, y `annotations`, donde va el mensaje que luego recibirá quien esté de guardia.

Algo que al principio me confundía es que Prometheus no envía correos ni mensajes. Él únicamente evalúa reglas y mantiene el estado de las alertas. El encargado de agruparlas, silenciarlas y enviarlas por correo, Slack o PagerDuty es Alertmanager.

Al final cada pieza tiene una responsabilidad bastante clara:

- el exporter obtiene las métricas;
- Prometheus las almacena;
- las recording rules precalculan consultas costosas;
- las alert rules detectan problemas;
- Alertmanager decide cómo y a quién avisar.

## Ejercicio 3 — Qué hay en la carpeta `01-start-up-loki`

Cuando levanté este laboratorio con `docker compose up` vi que realmente no se está ejecutando un único Loki, sino varios contenedores especializados.

La arquitectura es el modo Simple Scalable, donde la escritura y la lectura están separadas.

### docker-compose.yaml

Lo primero que arranca son tres contenedores de Loki:

- write
- read
- backend

Los tres utilizan exactamente la misma imagen (`grafana/loki`) y el mismo fichero de configuración.

La única diferencia es el parámetro `-target`, que indica qué función debe desempeñar cada proceso.

`write` recibe toda la ingesta de logs.

`read` responde las consultas que llegan desde Grafana.

`backend` ejecuta tareas internas como el compactor y el ruler.

Entre ellos se comunican mediante memberlist, usando el puerto 7946, sin necesidad de Consul ni etcd.

Después aparece MinIO.

En este laboratorio hace de almacenamiento S3. En lugar de guardar los logs en disco local, Loki escribe tanto los índices como los chunks dentro de dos buckets de MinIO.

Todo queda persistido en el directorio `.data/minio`, por lo que al reiniciar el laboratorio los datos siguen estando disponibles.

Otro componente importante es gateway.

Es un NGINX situado delante de todo el clúster.

Los clientes únicamente conocen el puerto 3100 del gateway.

Dependiendo de la URL, NGINX reenvía automáticamente la petición al servicio write o al servicio read.

Gracias a eso Grafana y Alloy no necesitan saber que internamente existen varios nodos distintos.

Después está Grafana Alloy, que sustituye al antiguo Promtail.

Se conecta al socket de Docker para descubrir automáticamente qué contenedores están ejecutándose y leer sus logs.

Su interfaz web de depuración queda disponible en el puerto 12345.

También se levanta Grafana, ya preparada con un datasource hacia Loki.

No tuve que configurarlo manualmente porque el laboratorio ya lo deja apuntando al gateway e incluye la cabecera `X-Scope-OrgID: tenant1`, necesaria porque Loki trabaja en modo multi-tenant.

Por último aparece flog.

Es simplemente un generador de logs aleatorios en formato JSON.

Su única función es producir tráfico para comprobar que toda la cadena funciona sin tener que desplegar una aplicación real.

Nada más arrancar ya empiezan a aparecer logs en Grafana.

### alloy-local-config.yaml

La configuración de Alloy es bastante sencilla.

Primero descubre los contenedores Docker.

Después añade como etiqueta el nombre del contenedor.

A continuación empieza a leer sus logs.

Finalmente los envía al endpoint:

```
http://gateway:3100/loki/api/v1/push
```

utilizando el tenant `tenant1`.

Es literalmente una tubería desde Docker hasta Loki.

### loki-config.yaml

Los tres procesos de Loki utilizan exactamente el mismo fichero de configuración.

Lo más importante que vi al revisarlo fue:

- descubrimiento mediante memberlist;
- almacenamiento TSDB;
- backend S3 apuntando a MinIO;
- `insecure: true`, porque todo funciona localmente;
- `s3forcepathstyle: true`, necesario para MinIO;
- `replication_factor: 1`, suficiente para un laboratorio.

Si se sigue el recorrido completo de un log queda bastante claro:

```
flog
 ↓
Docker
 ↓
Alloy
 ↓
Gateway
 ↓
Write
 ↓
MinIO
```

Y cuando Grafana hace una consulta ocurre exactamente el camino contrario:

```
Grafana
 ↓
Gateway
 ↓
Read
 ↓
MinIO
```

Mientras tanto el backend va ejecutando las tareas de mantenimiento en segundo plano.

## Ejercicio 4 — Cómo se estructura una traza en Jaeger

Lo entendí bastante mejor utilizando HotROD que leyendo la teoría.

Cuando lanzaba una petición desde la aplicación, Jaeger permitía seguir todo el recorrido que hacía entre los distintos microservicios.

### Trace

La traza representa una petición completa.

En HotROD una única petición pasaba por el frontend, después llamaba a customer, driver y route, y alguno de ellos terminaba consultando Redis.

Aunque cada servicio genera información por separado, todos comparten el mismo `trace_id`, que va viajando en las cabeceras HTTP.

Gracias a ese identificador Jaeger puede reconstruir el recorrido completo.

### Span

Cada operación individual de la traza es un span.

Puede ser una petición HTTP, una consulta SQL, una llamada a Redis o cualquier operación instrumentada.

El primero es el root span, que representa toda la petición desde el punto de vista del usuario.

En la interfaz de Jaeger los spans aparecen como un diagrama temporal parecido a un Gantt.

Eso fue lo que más me ayudó durante el laboratorio, porque permitía ver enseguida qué operaciones estaban ejecutándose en paralelo, cuáles iban encadenadas y cuál era realmente la que estaba consumiendo tiempo.

### Instrumentation scope

El instrumentation scope no describe la operación, sino quién la generó.

Normalmente aparece el nombre de la librería que creó ese span.

En HotROD aparecían entradas como:

```
otel.scope.name = redis-manual
```

Eso permite distinguir fácilmente entre spans creados automáticamente por una librería y spans añadidos manualmente por el desarrollador.

### Tags

Los tags (o atributos en OpenTelemetry) son pares clave-valor asociados a cada span.

Por ejemplo:

```
http.method=GET
db.system=redis
error=true
```

Resultan muy útiles para filtrar trazas desde Jaeger.

Durante la práctica los utilicé para localizar rápidamente los spans asociados a errores de Redis, ya que bastaba filtrar por `error=true`.

No hay que confundirlos con los logs del span, que representan eventos ocurridos durante su ejecución, ni con los process tags, que son datos comunes del proceso que generó todos los spans.
