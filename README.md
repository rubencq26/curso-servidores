# Curso: PostgreSQL + FastAPI desde cero

> Apuntes del curso. Cada lección añade una sección. Yo (Rubén) escribo el código;
> Claude revisa y explica.

**Entorno:** WSL2 (Ubuntu 24.04) · Python 3.14 (el del `.venv`) · PostgreSQL en **Docker** (Docker Desktop en Windows)

---

## Temario

| # | Lección | Estado |
|---|---------|--------|
| 1 | Qué es un servidor PostgreSQL y levantarlo con Docker | ✅ |
| 2 | `psql`: conectarse, roles, bases de datos y permisos | ✅ |
| 3 | SQL básico: tablas, tipos, claves, CRUD | ✅ |
| 4 | Relaciones: claves foráneas, JOINs, índices | ✅ |
| 5 | Proyecto Python: entorno virtual, dependencias, variables de entorno | ✅ |
| 6 | FastAPI: primer endpoint, rutas, Swagger (`/docs`) | ✅ |
| 7 | Conectar FastAPI con PostgreSQL (pool de conexiones) | ✅ |
| 8 | CRUD completo con Pydantic (validación de entrada/salida) | ✅ (falta la errata `lenght`, ver 8.12) |
| 9 | Errores, códigos HTTP y paginación | ⏳ en curso |
| 10 | Seguridad básica: SQL injection, credenciales, usuario de solo-lectura | ⬜ |
| 11 | Trabajar contra un Postgres que **ya existe** (el caso del trabajo) | ⬜ |
| 12 | SQLAlchemy: query builder y ORM (y migraciones con Alembic) | ⬜ |

---

## Lección 1 — Qué es un servidor PostgreSQL e instalarlo

### 1.1 La idea general

```
 [Cliente HTTP]  ──HTTP──▶  [API FastAPI]  ──SQL (puerto 5432)──▶  [Servidor PostgreSQL]  ──▶ [disco]
 navegador, curl,           tu código Python                      proceso que guarda
 frontend...                (endpoints)                           y consulta datos
```

- **PostgreSQL es un servidor**: un proceso que está siempre corriendo, escuchando
  en un puerto de red (por defecto **5432**), esperando que alguien se conecte y le
  mande SQL.
- **Tú nunca tocas los ficheros de datos directamente.** Siempre hablas con el
  servidor a través de un **cliente** (`psql`, DBeaver, pgAdmin, o tu código Python).
- **Los endpoints no los tiene Postgres.** Postgres solo entiende SQL. Los
  endpoints (`GET /usuarios`, `POST /pedidos`...) viven en la **API** (FastAPI),
  que hace de intermediaria: recibe HTTP → ejecuta SQL → devuelve JSON.

> 💡 Frase clave para el trabajo: *"nos dan el servidor Postgres y metemos
> endpoints"* = **construir una API que se conecta a ese Postgres**. El Postgres
> no se modifica para tener endpoints.

### 1.2 Vocabulario básico

| Término | Qué es |
|---|---|
| **Servidor / instancia / cluster** | El proceso de Postgres corriendo. *Ojo:* en Postgres "cluster" = una instancia con su carpeta de datos, no varias máquinas. |
| **Base de datos (database)** | Un contenedor dentro del servidor. Un servidor tiene varias. |
| **Esquema (schema)** | Una "carpeta" dentro de una base de datos. Por defecto: `public`. |
| **Tabla** | Donde viven los datos, en filas y columnas. |
| **Rol (role)** | Usuario de Postgres. Tiene contraseña y permisos. *No es* tu usuario de Linux. |
| **Cliente** | Programa que se conecta al servidor: `psql`, DBeaver, Python... |

Jerarquía: `servidor → base de datos → esquema → tabla → filas`

### 1.3 Los 5 datos para conectarse

Para conectarte a **cualquier** Postgres (el tuyo o el del trabajo) necesitas:

1. **host** – dónde está (`localhost`, una IP, un dominio)
2. **port** – normalmente `5432`
3. **database** – a qué base de datos
4. **user** – el rol
5. **password**

Normalmente se juntan en una **URL de conexión**:

```
postgresql://usuario:contraseña@host:5432/nombre_bd
```

> 💡 Mañana en el trabajo, lo primero que hay que pedir son estos 5 datos
> (y qué permisos tiene vuestro usuario: ¿solo leer? ¿crear tablas?).

### 1.4 ¿Por qué Docker?

En vez de instalar Postgres "a pelo" en el sistema, lo ejecutamos dentro de un
**contenedor**:

- **Limpio:** no ensucia tu sistema. Lo borras y no queda rastro.
- **Reproducible:** la misma versión exacta en tu PC, en el de un compañero y en el servidor.
- **Desechable:** si rompes algo aprendiendo, lo borras y lo vuelves a crear en segundos.
- **Es lo que se usa en el mundo real** para entornos de desarrollo.

### 1.5 Conceptos de Docker que necesitas

| Concepto | Qué es | Analogía |
|---|---|---|
| **Imagen** | Plantilla de solo lectura con el programa ya instalado (p. ej. `postgres:17`). Se descarga de Docker Hub. | El instalador / la receta |
| **Contenedor** | Una imagen **en ejecución**. Puedes tener varios de la misma imagen. | El programa abierto / el plato cocinado |
| **Volumen** | Almacenamiento que vive **fuera** del contenedor. | Un disco duro externo |
| **Mapeo de puertos** (`-p`) | Conecta un puerto de tu máquina con uno del contenedor. | Un desvío de llamadas |
| **Variables de entorno** (`-e`) | Configuración que le pasas al arrancar (usuario, contraseña...). | Rellenar un formulario |

> ⚠️ **Lo más importante:** un contenedor es **efímero**. Si lo borras sin un
> **volumen**, **pierdes todos los datos** de la base de datos. Para Postgres,
> siempre hay que usar un volumen.

### 1.6 Docker en WSL2

Docker Desktop corre en Windows y "presta" el motor a WSL. Para activarlo:
Docker Desktop → **Settings → Resources → WSL Integration** → activar la
distro **Ubuntu** → *Apply & restart*.

Comprobación:
```bash
docker --version          # el cliente existe
docker run hello-world    # el motor funciona de verdad
```

**Qué pasó en `docker run hello-world`** (lo explica el propio mensaje):

1. El **cliente** (`docker`, lo que tecleas) habló con el **daemon** (el motor, en Docker Desktop).
2. El daemon no tenía la imagen en local → la **descargó (pull)** de Docker Hub.
   `hello-world` = `hello-world:latest` (si no pones etiqueta, usa `latest`).
3. Creó un **contenedor** a partir de la imagen y lo ejecutó.
4. El programa imprimió el mensaje y **terminó** → el contenedor se paró.

> 💡 Un contenedor vive **lo que vive su proceso principal**. `hello-world`
> imprime y acaba. Un servidor (Postgres) se queda escuchando para siempre,
> así que su contenedor sigue vivo.

### 1.7 Puertos: el error más típico

Un contenedor tiene **su propia red**, separada de la de tu máquina. Postgres
escucha **dentro** del contenedor en el **5432**. Para llegar desde fuera hay
que hacer un "desvío":

```
-p PUERTO_DE_TU_MAQUINA:PUERTO_DENTRO_DEL_CONTENEDOR
       (lo eliges tú)        (lo decide el programa)
```

| Ejemplo | Significado |
|---|---|
| `-p 5432:5432` | Lo normal: mismo puerto fuera y dentro. |
| `-p 5433:5432` | Útil si ya tienes otro Postgres usando el 5432 en tu máquina. |
| `-p 8000:5432` | ❌ Funciona, pero confunde: **8000 es el puerto típico de FastAPI**. |

> ⚠️ El lado derecho **no lo eliges tú**: es donde escucha el programa. Para
> Postgres es 5432. Si pones `-p 5432:8000` no funcionará, porque dentro
> nadie escucha en el 8000.

Puertos que vamos a usar en el curso:
- **5432** → PostgreSQL
- **8000** → nuestra API FastAPI

### 1.8 Piezas de `docker run` para Postgres

| Pieza | Para qué |
|---|---|
| `docker run` | Crear y arrancar un contenedor |
| `-d` | *detached*: en segundo plano (te devuelve la terminal) |
| `--name NOMBRE` | Darle un nombre fácil (si no, Docker inventa uno tipo `happy_turing`) |
| `-e POSTGRES_PASSWORD=...` | **Variable de entorno**: la imagen oficial la **exige**; es la contraseña del superusuario `postgres` |
| `-e POSTGRES_USER=...` / `-e POSTGRES_DB=...` | Opcionales: otro superusuario / crear una BD al arrancar |
| `-p 5432:5432` | Mapeo de puertos |
| `-v NOMBRE_VOLUMEN:/var/lib/postgresql/data` | **Volumen**: guarda los datos fuera del contenedor. La ruta de la derecha es donde Postgres (≤17) guarda sus datos dentro del contenedor |
| `postgres:17` | La **imagen** con su **etiqueta** (versión). Va **al final** |

> ⚠️ **Fija siempre la versión** (`postgres:17`, no `postgres` a secas).
> `latest` cambia con el tiempo y un día te cambia la versión mayor sin avisar.
> En el trabajo, pregunta **qué versión** de Postgres tiene su servidor y usa la
> misma en local.
>
> Nota: desde **Postgres 18** la imagen guarda los datos en
> `/var/lib/postgresql` (no en `.../data`). Si usas 18+, el volumen se monta ahí.

### 1.9 Depurar un contenedor que no arranca

**Caso real del curso.** Primer intento:

```bash
docker run -d --name curso-postgres -e POSTGRES_DB=db1234 -e POSTGRES_DB=curso ...
#                                      ^^^^^^^^^^^ debía ser POSTGRES_PASSWORD
```

- `-d` devolvió la terminal **sin error**: con `-d` Docker solo te dice "lo he
  arrancado", **no** que el programa de dentro funcione.
- Al repetir `POSTGRES_DB`, **gana la última** (`curso`). La contraseña nunca llegó.
- El contenedor murió al segundo → `docker ps` no lo enseña (solo muestra los vivos).

**Método para depurar:**

```bash
docker ps -a                  # TODOS los contenedores, también los muertos → STATUS "Exited (1)"
docker logs curso-postgres    # ¿qué dijo el programa antes de morir?
```

El log lo decía clarísimo:

```
Error: Database is uninitialized and superuser password is not specified.
       You must specify POSTGRES_PASSWORD to a non-empty value...
```

> 💡 **Regla:** `Exited (0)` = terminó bien · `Exited (≠0)` = terminó con error →
> mira **siempre** `docker logs` antes de tocar nada.

**Para reintentar** hay que borrar el contenedor viejo, porque el **nombre
ya está cogido** (si no, `docker run` da error de *conflict*):

```bash
docker rm curso-postgres      # borra el contenedor (NO borra el volumen)
```

> ⚠️ **Trampa importante:** las variables `POSTGRES_PASSWORD`, `POSTGRES_USER`
> y `POSTGRES_DB` **solo se aplican la primera vez**, cuando el volumen está
> vacío. Si el volumen ya tiene una base de datos inicializada, Postgres las
> **ignora**. Si te equivocas de contraseña después de inicializar, cambiar
> el `-e` no sirve: o la cambias por SQL o borras el volumen
> (`docker volume rm curso-pgdata`) y **pierdes los datos**.
> Aquí no pasa nada porque la inicialización falló antes de escribir nada.

### 1.10 Levantar Postgres en un contenedor ✅

```bash
docker run -d \
  --name curso-postgres \
  -e POSTGRES_PASSWORD=db1234 \
  -e POSTGRES_DB=curso \
  -p 5432:5432 \
  -v curso-pgdata:/var/lib/postgresql/data \
  postgres:17
```

(La `\` al final de línea solo sirve para partir un comando largo en varias líneas.)

**Cómo leer `docker ps`:**

```
CONTAINER ID   IMAGE         COMMAND                  CREATED         STATUS         PORTS                       NAMES
76d68fd0564c   postgres:17   "docker-entrypoint.s…"   4 seconds ago   Up 4 seconds   0.0.0.0:5432->5432/tcp      curso-postgres
```

- `STATUS: Up ...` → vivo. (Si en `docker ps -a` pone `Exited`, está muerto.)
- `PORTS: 0.0.0.0:5432->5432/tcp` → el puerto 5432 de **tu máquina** (`0.0.0.0` = todas
  sus interfaces de red) va al 5432 **del contenedor**.
- `COMMAND: docker-entrypoint.s…` → script de la imagen que, la primera vez,
  **inicializa** la BD (crea el usuario y la BD usando las variables `-e`) y luego arranca Postgres.

**Confirmación definitiva** en los logs:

```
LOG:  database system is ready to accept connections
```

> 💡 "Up" significa que el contenedor está vivo. "ready to accept connections"
> significa que **Postgres** está listo. No son lo mismo: los primeros segundos
> el contenedor está "Up" pero Postgres todavía se está inicializando.

### 1.11 Ciclo de vida: comandos del día a día

```bash
docker stop curso-postgres     # parar (los datos siguen en el volumen)
docker start curso-postgres    # volver a arrancar con la MISMA config (no hace falta repetir el run)
docker logs -f curso-postgres  # ver logs en directo (Ctrl+C para salir)
docker rm curso-postgres       # borrar el contenedor (tiene que estar parado). El volumen SE QUEDA
docker volume ls               # ver volúmenes
docker volume rm curso-pgdata  # ⚠️ borrar el volumen = borrar TODOS los datos
```

> 💡 `docker run` = **crear** + arrancar (una sola vez). `docker start` = arrancar
> uno que ya existe. Después de reiniciar el PC: `docker start curso-postgres`.

**¿Por qué `docker rm` no borra el volumen?** Por diseño: el contenedor es
desechable, los datos no. Puedes borrar el contenedor para cambiar la versión
de la imagen o la configuración, crear uno nuevo apuntando al mismo volumen
y tus datos siguen ahí.

---

## Lección 2 — `psql`: conectarse, roles y bases de datos

### 2.1 Entrar con `psql` dentro del contenedor

`psql` es el cliente oficial de línea de comandos. No lo tenemos instalado en
WSL, pero **la imagen de Postgres lo trae dentro**:

```bash
docker exec -it curso-postgres psql -U postgres -d curso
```

| Pieza | Qué hace |
|---|---|
| `docker exec` | Ejecuta un comando **dentro** de un contenedor que ya está corriendo |
| `-it` | Modo interactivo con terminal (para poder escribir dentro) |
| `curso-postgres` | En qué contenedor |
| `psql` | El programa a ejecutar |
| `-U postgres` | Con qué **rol** (usuario de Postgres) |
| `-d curso` | A qué **base de datos** |

> 💡 No pide contraseña porque te conectas **desde dentro** del contenedor
> (por *socket* local), y la imagen confía en las conexiones locales. Desde
> fuera (tu API en Python) **sí** la pedirá.

El prompt cambia a `curso=#`:
- `curso` → la base de datos en la que estás
- `#` → eres **superusuario** (un usuario normal ve `>`)

**Error típico: URL mal escrita.**

```bash
docker exec -it curso-postgres psql postregsql://api_curso:api1234@localhost:5432/curso
#                                   ^^^^^^^^^^ errata
psql: error: connection to server on socket "/var/run/postgresql/.s.PGSQL.5432" failed:
FATAL:  role "root" does not exist
```

`psql` solo reconoce una URL si empieza **exactamente** por `postgresql://` o
`postgres://`. Si no, toma ese texto como el **nombre de una base de datos** y
usa los valores por defecto para todo lo demás. El error lo delata:
- `on socket` → no ha ido a `localhost` por red: **ha ignorado el host** de la URL.
- `role "root"` → no ha usado `api_curso`: ha usado el usuario del sistema
  operativo. `docker exec` ejecuta como `root` dentro del contenedor.

> 💡 Cuando un error menciona un usuario, host o puerto que **tú no has puesto**,
> es que tu configuración **no se está leyendo**. Lo primero que hay que revisar
> es la escritura de la URL o de la variable.

### 2.2 Metacomandos de `psql` (empiezan por `\`)

No son SQL, son atajos del propio `psql`. **No llevan `;`**.

| Comando | Qué hace |
|---|---|
| `\conninfo` | ¿Dónde estoy conectado y con qué usuario? |
| `\l` | Listar bases de datos |
| `\du` | Listar roles (usuarios) |
| `\dn` | Listar esquemas |
| `\dt` | Listar tablas (del esquema actual) |
| `\d nombre_tabla` | Describir una tabla (columnas, tipos, índices) |
| `\c otra_bd` | Cambiar a otra base de datos |
| `\?` | Ayuda de metacomandos |
| `\h SELECT` | Ayuda de un comando SQL |
| `\q` | Salir |

> ⚠️ El SQL normal **sí** necesita `;` al final. Si te olvidas, `psql` cree que
> no has terminado y el prompt cambia a `curso-#` esperando más. Escribe `;` y Enter.

### 2.3 Lo que hay en un Postgres recién creado

**`\du` — roles:**

```
 Role name |                         Attributes
-----------+------------------------------------------------------------
 postgres  | Superuser, Create role, Create DB, Replication, Bypass RLS
```

| Atributo | Significa |
|---|---|
| **Superuser** | Se salta **todas** las comprobaciones de permisos. Puede borrar cualquier cosa, leer cualquier tabla, incluso ejecutar comandos en el servidor. |
| **Create role** | Puede crear, modificar y borrar otros roles. |
| **Create DB** | Puede crear bases de datos. |
| **Replication** | Puede hacer copias en tiempo real del servidor (réplicas). |
| **Bypass RLS** | Se salta la *Row Level Security* (reglas de "este usuario solo ve sus filas"). |

> ⚠️ **Principio de mínimo privilegio:** una API **nunca** debe conectarse
> como `postgres`. Si alguien encuentra un fallo en tu API (p. ej. una SQL
> injection), hereda **todos** los permisos del usuario con el que conecta.
> Con `postgres` = control total del servidor. Con un rol limitado = solo
> puede tocar lo que ese rol pueda tocar.
>
> En el trabajo lo normal es que os den un rol propio para la API con
> permisos concretos (p. ej. leer/escribir ciertas tablas de un esquema).

**`\dn` — esquemas:**

```
  Name  |       Owner
--------+-------------------
 public | pg_database_owner
```

- Toda base de datos nueva trae el esquema `public`, y si no dices otra cosa,
  las tablas se crean ahí.
- `pg_database_owner` no es una persona: es un **rol especial** que significa
  "quien sea el dueño de esta base de datos". (Desde Postgres 15, en `public`
  solo puede crear tablas el dueño de la BD, no cualquiera. Antes podía todo el mundo.)

**`\dt` — tablas:** `Did not find any relations.` → la BD `curso` está vacía.
*Relation* es el nombre técnico que usa Postgres para tablas, vistas, etc.

**`\l` — bases de datos:** aunque solo creamos `curso`, salen 4:

| BD | Para qué existe |
|---|---|
| `curso` | La nuestra (la creó `POSTGRES_DB=curso`). |
| `postgres` | BD "por defecto" vacía, para tener **siempre** a dónde conectarse (p. ej. para crear o borrar otras BDs: no puedes borrar la BD en la que estás conectado). |
| `template1` | **Plantilla** que se **copia** cada vez que haces `CREATE DATABASE`. Si le añades algo, todas las BDs nuevas lo tendrán. |
| `template0` | Copia **intacta** de fábrica de `template1`, por si la estropeas. No admite conexiones. |

> 💡 Mañana, en el servidor del trabajo, haz `\l` nada más entrar: verás
> qué bases de datos hay y cuál es la vuestra. Ignora `postgres`, `template0` y `template1`.

**Columna `Access privileges`:** permisos sobre la base de datos, con el formato
`quién=permisos/quién_los_dio`. Si `quién` está vacío, se refiere a `PUBLIC` (todos los roles).

| Letra | Permiso |
|---|---|
| `c` | CONNECT (conectarse) |
| `C` | CREATE (crear esquemas dentro) |
| `T` | TEMPORARY (crear tablas temporales) |

- `=c/postgres` → todos pueden conectarse (lo concedió `postgres`).
- `postgres=CTc/postgres` → `postgres` tiene los tres.
- Vacío (como en `curso`) → permisos **por defecto**: el dueño puede todo y `PUBLIC` puede conectar y crear tablas temporales.

**`\conninfo`:**
`connected to database "curso" as user "postgres" via socket in "/var/run/postgresql"`

- **via socket** = conexión **local** por un fichero especial del sistema, sin pasar por la red.
  Solo es posible estando **dentro** del contenedor.
- Tu API se conectará **por TCP** (por red): `localhost:5432`.

### 2.4 La URL de conexión (corregida)

Error típico (el mío en el curso):

```
❌ http://localhost:5432?POSTGRES_PASSWORD=db1234&POSTGRES_DB=curso
```

1. **`http://` no**: Postgres **no habla HTTP**, tiene su propio protocolo. Lo
   que habla HTTP es la API (FastAPI). El esquema es `postgresql://`.
2. **`POSTGRES_PASSWORD` / `POSTGRES_DB` no son datos de conexión**: son
   variables que lee la **imagen de Docker** para *inicializar* el servidor la
   primera vez. Un cliente no sabe nada de ellas.
3. **Faltaba el usuario.**

```
✅ postgresql://postgres:db1234@localhost:5432/curso
   └protocolo┘ └usuario┘└pass┘ └─host──┘└port┘└─BD─┘
```

> ⚠️ **Ojo con la palabra "esquema", que en español significa dos cosas:**
> - **URL scheme** (protocolo): el `postgresql://` o `http://` del principio de una URL.
> - **Schema de Postgres**: la "carpeta" dentro de una BD (`public`).
>
> **El schema de Postgres no va en la URL.** Te conectas a una **base de
> datos**; el schema se elige después, en el SQL:
>
> ```sql
> SELECT * FROM public.usuarios;   -- schema explícito: schema.tabla
> SELECT * FROM usuarios;          -- sin schema → Postgres lo busca en el search_path
> SHOW search_path;                -- por defecto: "$user", public
> ```
>
> `search_path` = lista de schemas donde Postgres busca cuando no pones el
> prefijo. Por defecto: primero un schema con tu mismo nombre de usuario (si
> existe), luego `public`. Por eso con `public` casi nunca hace falta escribirlo.
> En el trabajo, si las tablas están en otro schema (p. ej. `ventas`), tendréis que
> escribir `ventas.pedidos` o cambiar el `search_path`.

> ⚠️ Si la contraseña tiene caracteres especiales (`@`, `:`, `/`, `#`...) hay
> que **codificarlos** en la URL (p. ej. `@` → `%40`), si no, se rompe.

### 2.5 Crear un rol para la API

Sintaxis:

```sql
CREATE ROLE nombre_rol WITH LOGIN PASSWORD 'la_contraseña';
```

- `LOGIN` → puede **conectarse**. Sin `LOGIN`, un rol es solo un "grupo" de
  permisos (como un rol de "lectores" que luego asignas a usuarios).
  `CREATE USER` = `CREATE ROLE ... WITH LOGIN`, es un atajo.
- La contraseña va entre **comillas simples** `'...'`. En SQL, las comillas
  dobles `"..."` son para **nombres** (de tablas, columnas...), no para textos.
- Por defecto un rol nuevo **no** es superusuario, **no** puede crear BDs ni roles.

En el curso:

```sql
CREATE USER api_curso PASSWORD 'api1234';   -- → CREATE ROLE
```

(`WITH` es opcional: `CREATE USER x WITH PASSWORD '...'` es lo mismo.)

En `\du` aparece con la columna **Attributes vacía**. Vacío no significa "no
puede nada", significa "**ningún atributo especial**": no es superusuario,
no crea BDs ni roles. `LOGIN` no aparece en la lista porque es lo normal;
`\du` solo te avisa cuando un rol **no** puede entrar (`Cannot login`).

> 💡 Cuando ejecutas SQL, `psql` responde con una **etiqueta de comando**:
> `CREATE ROLE`, `CREATE TABLE`, `INSERT 0 1`... Si sale eso, ha ido bien. Si
> sale `ERROR: ...`, no se ha hecho nada.

Para probarlo, conéctate con ese rol **por TCP** (dando `-h localhost` o una URL,
`psql` usa la red en vez del socket):

```bash
docker exec -it curso-postgres psql "postgresql://nombre_rol:la_contraseña@localhost:5432/curso"
```

**Resultado en el curso**, comparado con la conexión como `postgres`:

| | Como `postgres` (socket) | Como `api_curso` (TCP) |
|---|---|---|
| `\conninfo` | `via socket in "/var/run/postgresql"` | `on host "localhost" (address "::1")` |
| Prompt | `curso=#` → superusuario | `curso=>` → usuario normal |

- `::1` es `localhost` en **IPv6** (`127.0.0.1` en IPv4). Es decir, ha ido por la red.
- No ha pedido la contraseña, pero **no** es porque fuera en la URL: ver 2.8,
  dentro del contenedor `localhost` también es de confianza (`trust`).

### 2.6 Primer "permission denied" (y cómo leer un error)

```
curso=> CREATE TABLE prueba (id int);
ERROR:  permission denied for schema public
LINE 1: CREATE TABLE prueba (id int);
                     ^
```

Cómo se lee:
- `ERROR:` → no se ha hecho **nada**.
- `permission denied for schema public` → **qué** permiso falta y **dónde**:
  no se puede crear en el schema `public`.
- `LINE 1` + `^` → en qué punto del SQL ha fallado (aquí, en el nombre de la tabla que intentaba crear).

**¿Por qué?** Desde **Postgres 15**, el dueño de `public` es `pg_database_owner`
(= el dueño de la BD, aquí `postgres`), y al resto de roles solo se les da
`USAGE` (usar lo que hay), **no** `CREATE` (crear cosas). En versiones
anteriores cualquiera podía crear tablas en `public`; se cambió por seguridad.

> 💡 **Esto es bueno, no un problema.** En un proyecto bien montado, la API
> **no crea tablas**: las tablas las crea un rol de administración (o las
> *migraciones*), y la API solo lee y escribe **datos**. Es muy probable que
> mañana vuestro usuario tampoco pueda crear tablas.

Si alguna vez te sale este error en un Postgres antiguo (≤14) y no te sale en
otro moderno, ya sabes por qué.

### 2.7 El modelo de permisos: edificio → planta → habitación

Para leer una tabla, un rol necesita permiso en **los tres niveles**:

| Nivel | Permiso | Analogía | SQL |
|---|---|---|---|
| **Base de datos** | `CONNECT` | Entrar en el edificio | `GRANT CONNECT ON DATABASE curso TO api_curso;` |
| **Schema** | `USAGE` (ver lo que hay) / `CREATE` (crear cosas) | Entrar en una planta / montar habitaciones nuevas | `GRANT USAGE ON SCHEMA public TO api_curso;` |
| **Tabla** | `SELECT`, `INSERT`, `UPDATE`, `DELETE` | Qué puedes hacer dentro de una habitación | `GRANT SELECT ON prueba TO api_curso;` |

- `GRANT permiso ON objeto TO rol;` → dar un permiso.
- `REVOKE permiso ON objeto FROM rol;` → quitarlo.
- Solo puede dar permisos el **dueño** del objeto (o un superusuario).
- Por defecto, `PUBLIC` (todos) ya tiene `CONNECT` en las BDs y `USAGE` en
  `public`. Por eso `api_curso` pudo entrar sin que le diéramos nada.
- Ver los permisos de las tablas: `\dp` (o `\dp nombre_tabla`).

**Leer `\dp`** (resultado del ejercicio tras `GRANT SELECT ON prueba TO api_curso;`):

```
 Schema |  Name  | Type  |     Access privileges
--------+--------+-------+----------------------------
 public | prueba | table | postgres=arwdDxtm/postgres+
        |        |       | api_curso=r/postgres
```

Mismo formato que en `\l`: `quién=permisos/quién_los_dio`. El `+` del final
solo indica que la celda sigue en la línea de abajo (es de `psql`, no un permiso).

| Letra | Permiso | Qué deja hacer |
|---|---|---|
| `r` | SELECT (*read*) | Leer filas |
| `a` | INSERT (*append*) | Añadir filas |
| `w` | UPDATE (*write*) | Modificar filas |
| `d` | DELETE | Borrar filas |
| `D` | TRUNCATE | Vaciar la tabla entera de golpe |
| `x` | REFERENCES | Crear claves foráneas que apunten a esta tabla |
| `t` | TRIGGER | Crear *triggers* sobre la tabla |
| `m` | MAINTAIN (Postgres 17+) | Mantenimiento: `VACUUM`, `ANALYZE`, `REINDEX`... |

- `postgres=arwdDxtm/postgres` → `postgres` es el **dueño**: tiene **todos** los permisos.
- `api_curso=r/postgres` → `api_curso` **solo puede leer**, y se lo dio `postgres`.

> 💡 Las 4 que importan para una API son **`arwd`** = el **CRUD**:
> **C**reate → `a` (INSERT) · **R**ead → `r` (SELECT) · **U**pdate → `w` · **D**elete → `d`.
> Una API típica: `GRANT SELECT, INSERT, UPDATE, DELETE ON tabla TO rol_api;`
> Una API de solo consulta (informes, dashboards): solo `SELECT`.

**Lo que pasó en el ejercicio de las dos terminales:**

| Paso | Resultado | Por qué |
|---|---|---|
| `SELECT` antes del GRANT | `permission denied for table prueba` | Ya pasa los niveles BD y schema; ahora falla en el **nivel tabla** |
| `GRANT SELECT ON prueba TO api_curso;` | `GRANT` | El dueño (`postgres`) da el permiso `r` |
| `SELECT` después | Funciona | Tiene `r` |
| `INSERT` | `permission denied for table prueba` | INSERT es `a`, y solo tiene `r` |

> ⚠️ Cuidado con decir "permiso de escritura": en Postgres **cada operación tiene
> su permiso**. Tener `UPDATE` (`w`) **no** deja hacer `INSERT` (`a`) ni `DELETE` (`d`).

**¿Por qué no hizo falta `CONNECT` ni `USAGE`?** No es por estar "en `public`":
es porque existe un pseudo-rol **`PUBLIC`** (= todos los roles, incluidos los
que se creen en el futuro) que **por defecto** tiene `CONNECT` en todas las BDs y
`USAGE` en el schema `public`. Lo que se le da a `PUBLIC` lo tiene todo el mundo.
Si el admin lo revoca (`REVOKE CONNECT ON DATABASE curso FROM PUBLIC;`), entonces
sí hay que darlo rol a rol. En servidores de empresa es habitual que lo hagan.

**¿Cómo dejar que un rol cree tablas?** Las tablas se crean **dentro de un schema**,
así que el permiso va en el **nivel schema**:

```sql
GRANT CREATE ON SCHEMA public TO api_curso;   -- puede crear tablas en public
```

Ojo, que existe uno parecido que hace **otra cosa**:

```sql
GRANT CREATE ON DATABASE curso TO api_curso;  -- puede crear SCHEMAS nuevos en la BD (no tablas en public)
```

**¿Quién puede dar permisos?**

1. El **superusuario** (cualquier permiso, sobre cualquier cosa).
2. El **dueño** del objeto (todos los permisos sobre lo suyo).
3. Quien recibió el permiso **`WITH GRANT OPTION`**:

```sql
GRANT SELECT ON prueba TO api_curso WITH GRANT OPTION;
-- api_curso ya puede hacer: GRANT SELECT ON prueba TO otro_rol;
```

En `\dp` se ve con un **asterisco** detrás de la letra: `api_curso=r*/postgres`
→ tiene `r` **y** puede darlo a otros. Solo puede repartir **lo que él tiene**
(con `r*` puede dar `SELECT`, pero no `INSERT`).

Quitarlo:

```sql
REVOKE GRANT OPTION FOR SELECT ON prueba FROM api_curso;  -- le quita solo la capacidad de repartir
REVOKE SELECT ON prueba FROM api_curso CASCADE;           -- le quita el permiso y, en cascada, a quien él se lo dio
```

> ⚠️ Rara vez se usa en la práctica: la gestión de permisos suele quedarse en manos
> del dueño/admin. Una **API nunca** debería tener `GRANT OPTION`: si la atacan,
> el atacante podría repartirse permisos.

**Forma profesional: roles de grupo.** En vez de dar permisos tabla a tabla y
usuario a usuario, se crea un rol **sin `LOGIN`** que hace de "grupo" y se mete
a los usuarios dentro:

```sql
CREATE ROLE lectores;                          -- sin LOGIN = es un grupo
GRANT SELECT ON ALL TABLES IN SCHEMA public TO lectores;
GRANT lectores TO api_curso;                   -- api_curso hereda los permisos de lectores
GRANT lectores TO ana WITH ADMIN OPTION;       -- ana además puede meter/sacar gente del grupo
```

- `ON ALL TABLES IN SCHEMA` = todas las tablas **que existen ahora** (las nuevas no; eso se hace con `ALTER DEFAULT PRIVILEGES`, lo veremos).
- `WITH ADMIN OPTION` es el equivalente de `GRANT OPTION` pero para **pertenencia a roles**.
- En `\du` verás la columna *Member of*.

### 2.8 `pg_hba.conf`: quién puede conectarse y cómo se autentica

Que te pida contraseña o no **no** depende del socket: lo decide el fichero
**`pg_hba.conf`** (*host-based authentication*). Es una lista de reglas que se
leen **de arriba abajo**, y se aplica **la primera que encaje**.

Las reglas de nuestro contenedor:

```
# TIPO   BD            USUARIO   ORIGEN          MÉTODO
local    all           all                       trust
host     all           all       127.0.0.1/32    trust
host     all           all       ::1/128         trust
local    replication   all                       trust
host     replication   all       127.0.0.1/32    trust
host     replication   all       ::1/128         trust
host     all           all       all             scram-sha-256
```

| Columna | Significa |
|---|---|
| **Tipo** | `local` = por socket · `host` = por red (TCP) |
| **BD / Usuario** | A qué bases de datos y roles aplica (`all` = todos) |
| **Origen** | Desde qué IP llega la conexión (`127.0.0.1` y `::1` = la propia máquina) |
| **Método** | `trust` = **entra sin contraseña** · `scram-sha-256` = **pide contraseña** (cifrada) · `reject` = prohibido |

**Aplicado a lo que hicimos:**

| Conexión | Regla que encaja | ¿Contraseña? |
|---|---|---|
| `docker exec ... psql -U postgres` (socket) | `local all all trust` | No |
| `docker exec ... psql "postgresql://api_curso:...@localhost..."` | `host ... 127.0.0.1/32 trust` (o `::1/128`) | **No** (aunque pongas una mal, entra) |
| `docker exec ... psql "postgresql://api_curso:...@$(hostname -i)..."` | Origen = IP del propio contenedor (`172.x.x.x`) → última regla | **Sí** |
| Desde WSL / tu API, por el puerto 5432 mapeado | Llega desde la red de Docker (`172.x.x.x`) → última regla, `scram-sha-256` | **Sí** |

#### "¿Pero si me he conectado por TCP y no por socket?"

Es la confusión típica (le pasó a Rubén: entró con `api12354` en vez de
`api1234`). Que la conexión sea TCP solo descarta las reglas `local`. Después,
Postgres sigue mirando **la IP de origen**, y ahí está la trampa:

```
docker exec -it curso-postgres psql "postgresql://...@localhost:5432/curso"
└──────────┬─────────────────┘                      └───┬───┘
  psql corre DENTRO del contenedor          "localhost" = el propio contenedor
                                            → la conexión llega desde 127.0.0.1
                                            → regla "host all all 127.0.0.1/32 trust"
                                            → trust: la contraseña NI SE MIRA
```

`localhost` no significa "mi portátil", sino **"la máquina donde se ejecuta el
programa"**. Con `docker exec`, el programa (`psql`) se ejecuta dentro del
contenedor, así que `localhost` es el contenedor.

**Cómo comprobar que la contraseña sí se valida:** conéctate desde un origen que
no sea `127.0.0.1`. Por ejemplo, dentro del contenedor pero usando su IP de
red (`hostname -i` la imprime):

```bash
docker exec -it curso-postgres sh -c 'psql "postgresql://api_curso:malapass@$(hostname -i):5432/curso"'
# FATAL:  password authentication failed for user "api_curso"   ← ahora sí la comprueba
```

O desde WSL con tu API/psycopg por el puerto 5432 mapeado: con una contraseña
mala en el `.env`, la API no arranca.

> 💡 **Regla para recordar:** `trust` = "me fío de quien venga de aquí, no
> compruebo nada". Que te deje entrar con una contraseña mala **no** significa
> que la contraseña esté bien: significa que nadie la ha mirado.

> 💡 La imagen oficial de Docker confía en todo lo que viene **de dentro** del
> contenedor y pide contraseña a todo lo que viene **de fuera**. Para desarrollo
> está bien; en un servidor real, `trust` en red sería una barbaridad.
>
> En el trabajo **no** vais a tocar `pg_hba.conf` (es cosa del administrador), pero
> si os sale `no pg_hba.conf entry for host "x.x.x.x"...`, significa que **ninguna
> regla deja entrar desde vuestra IP**: hay que pedirle al admin que la añada.

```bash
# ver las reglas activas del contenedor (sin comentarios ni líneas vacías)
docker exec curso-postgres sh -c 'grep -v "^#" "$PGDATA/pg_hba.conf" | grep -v "^$"'
# $PGDATA = carpeta de datos de Postgres dentro del contenedor (comillas simples
# por fuera → la variable la expande el shell del contenedor, no el tuyo)
```

### 2.9 🧭 Chuleta para el primer día: explorar un Postgres que te dan

Cuando os den el servidor, conéctate con **vuestro** usuario y recorre esto:

```
\conninfo                    -- ¿con quién y dónde estoy?
SELECT version();            -- ¿qué versión de Postgres? (usa la misma en local)
\l                           -- ¿qué BDs hay? (ignora postgres, template0, template1)
\dn                          -- ¿qué schemas hay en esta BD?
SHOW search_path;            -- ¿dónde busca si no pongo schema?
\dt nombre_schema.*          -- tablas de un schema concreto (\dt *.* = todas)
\d nombre_schema.tabla       -- columnas y tipos de una tabla
\dp nombre_schema.tabla      -- ¿qué puedo hacer en esta tabla? busca vuestro rol: arwd
\du                          -- roles y sus atributos
```

Preguntas que hay que hacer al que os da el acceso:
1. Los 5 datos de conexión (host, puerto, BD, usuario, contraseña) y **desde qué IPs** se permite entrar.
2. ¿Nuestro usuario puede crear tablas o solo trabajar con datos? ¿En qué schema?
3. ¿Hay un entorno de **pruebas** separado del de producción?

---

## Lección 3 — SQL básico: tablas, tipos, claves, CRUD

### 3.1 Anatomía de `CREATE TABLE`

```sql
CREATE TABLE prueba (id int);
--           ^^^^^^  ^^^^^^^^
--           nombre  lista de COLUMNAS entre paréntesis
```

Lo que va entre paréntesis es la **definición de las columnas**: cada una es
`nombre tipo`, separadas por **comas**. `prueba (id int)` = una tabla con una
sola columna llamada `id` que guarda números enteros.

Una tabla más realista:

```sql
CREATE TABLE usuarios (
    id         int,
    nombre     text,
    email      text,
    activo     boolean,
    creado_en  timestamp
);
```

- Una columna por línea solo por legibilidad; a Postgres le da igual.
- La **última** columna **no** lleva coma (error muy típico: `syntax error at or near ")"`).
- Las columnas se definen al crear la tabla; las **filas** (los datos) se añaden
  después con `INSERT`.

```
          columnas →  id | nombre | email          | activo
filas ↓             ----+--------+----------------+--------
                      1 | Ana    | ana@mail.com   | true
                      2 | Luis   | luis@mail.com  | false
```

**Tipos más usados:**

| Tipo | Guarda | Ejemplo |
|---|---|---|
| `int` / `integer` | Número entero (hasta ~2.100 millones) | `42` |
| `bigint` | Entero grande | `9000000000` |
| `numeric(10,2)` | Decimal **exacto** (usar para **dinero**) | `1999.99` |
| `text` | Texto de cualquier longitud | `'Ana'` |
| `varchar(100)` | Texto con un máximo de caracteres | `'Ana'` |
| `boolean` | Verdadero / falso | `true` |
| `date` | Fecha | `'2026-11-12'` |
| `timestamptz` | Fecha y hora **con zona horaria** (la recomendada) | `now()` |

> 💡 El tipo **importa**: Postgres rechaza datos que no encajan. Si intentas
> meter `'hola'` en una columna `int` → `ERROR: invalid input syntax for type integer`.
> Esta validación gratis es una de las grandes ventajas de una BD relacional.

Además del tipo, cada columna puede llevar **restricciones** (`PRIMARY KEY`,
`NOT NULL`, `UNIQUE`, `DEFAULT`...). Las vemos en la sección 3.4.

### 3.2 `INSERT` y cómo leer sus errores

```sql
INSERT INTO usuarios (id, nombre, email, activo) VALUES (1, 'Ana', 'ana@mail.com', true);
--                    └──── columnas ─────────┘          └──── valores, MISMO orden ──┘
```

Respuesta: `INSERT 0 1` → el `1` = **filas insertadas**. (El `0` es un resto
histórico, ignóralo.)

Errores que salieron en el curso:

| SQL | Error | Por qué |
|---|---|---|
| `VALUES (2, 'Juan', , true)` | `syntax error at or near ","` | No se puede dejar un hueco vacío entre comas |
| `(id, nombre, email, activo) VALUES (2, 'Juan', true)` | `INSERT has more target columns than expressions` | 4 columnas pero 3 valores: tienen que coincidir |

### 3.3 `NULL`: "no hay valor"

Dos formas de dejar una columna sin valor:

```sql
INSERT INTO usuarios (id, nombre, activo) VALUES (2, 'Juan', true);               -- omitir la columna
INSERT INTO usuarios (id, nombre, email, activo) VALUES (2, 'Juan', NULL, true);  -- NULL explícito
```

- `NULL` **no** es `''` (texto vacío) ni `0`: es **"desconocido / no hay dato"**.
- Si omites una columna, recibe su `DEFAULT`; si no tiene, `NULL`. (Por eso
  `creado_en` salió vacío en todas las filas.)
- ⚠️ `psql` pinta `NULL` como **un hueco en blanco**, igual que `''`. Para distinguirlos:
  `\pset null '∅'` (dura hasta que salgas de `psql`).
- ⚠️ Para buscar nulos **no** sirve `=`: `WHERE email = NULL` no devuelve nada nunca.
  Se usa `WHERE email IS NULL` / `IS NOT NULL`.
- En la API (JSON), `NULL` de Postgres se convierte en `null`, y `None` en Python.

### 3.4 Restricciones (constraints): que la tabla se defienda sola

**El problema** (lo que pasó en el curso): sin restricciones, la tabla aceptó
**tres usuarios con `id = 2`** y uno **sin email**. Si la API recibe
`GET /usuarios/2`, ¿cuál devuelve? Encuentra 3 filas cuando esperaba 1 → o
devuelve uno al azar o falla. **Los datos basura acaban siendo bugs en la API.**

> 💡 **Regla de oro:** las reglas de los datos se ponen **en la base de datos**,
> no solo en la API. La API puede tener fallos, puede haber otra app escribiendo
> en la misma BD, o alguien puede meter datos a mano. La BD es la última defensa.

| Restricción | Qué garantiza |
|---|---|
| `NOT NULL` | La columna **siempre** tiene valor |
| `UNIQUE` | No hay dos filas con el mismo valor en esa columna (los `NULL` sí se pueden repetir) |
| `PRIMARY KEY` | El **identificador** de la fila: = `NOT NULL` + `UNIQUE` (y crea un índice). **Solo una por tabla** |
| `DEFAULT valor` | Valor que se pone si no le das uno al insertar |
| `CHECK (condición)` | Cualquier regla: `CHECK (precio >= 0)`, `CHECK (edad BETWEEN 0 AND 150)` |

**Ids automáticos.** No queremos inventarnos el `id` a mano (¿cuál era el
siguiente libre?). Postgres lo genera:

```sql
id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY
```

- `GENERATED ALWAYS AS IDENTITY` → Postgres lleva un contador interno (1, 2, 3...).
- `ALWAYS` → **no** te deja poner el id a mano (error si lo intentas).
  `BY DEFAULT` sí te dejaría.
- Verás mucho `id SERIAL PRIMARY KEY` en código antiguo y tutoriales: es la forma
  vieja de hacer lo mismo. Si el servidor del trabajo lo usa, funciona igual.
- Los ids **no se reutilizan**: si borras el 3, el siguiente sigue siendo el 4.
  Y si un `INSERT` falla, ese número también se pierde. Los huecos son normales.

**Fechas automáticas:** `creado_en timestamptz NOT NULL DEFAULT now()`.

**Dónde se escriben.** Detrás del tipo de cada columna, separadas por
**espacios** (no comas), en cualquier orden:

```
nombre_columna  TIPO  RESTRICCIÓN  RESTRICCIÓN  ...  ,
```

Ejemplo con otra tabla:

```sql
CREATE TABLE productos (
    codigo     text          PRIMARY KEY,
    nombre     text          NOT NULL,
    precio     numeric(10,2) NOT NULL CHECK (precio >= 0),
    stock      int           NOT NULL DEFAULT 0,
    sku        text          UNIQUE
);
```

- La **coma** separa **columnas**; los **espacios** separan las restricciones de una misma columna.
- `stock` → si no le das valor en el `INSERT`, vale `0`; y nunca puede ser `NULL`.
- `sku` → `UNIQUE` sin `NOT NULL`: puede quedar vacío, pero si se rellena no puede repetirse.

**Restricciones de tabla** (al final, como si fueran una "columna" más). Se usan
cuando la regla afecta a **varias columnas** a la vez:

```sql
CREATE TABLE notas (
    alumno_id  int  NOT NULL,
    asignatura text NOT NULL,
    nota       numeric(4,2),
    UNIQUE (alumno_id, asignatura)          -- un alumno, una nota por asignatura
);
```

**Ponerles nombre** (opcional, pero hace los errores más legibles):

```sql
precio numeric(10,2) CONSTRAINT precio_positivo CHECK (precio >= 0)
```

Sin nombre, Postgres se inventa uno (p. ej. `productos_precio_check`), que es lo
que verás en los mensajes de error.

**Ver las restricciones de una tabla:** `\d nombre_tabla` (abajo, en *Indexes*
y *Check constraints*).

**Ejercicio del curso: la tabla `usuarios` con restricciones**

```sql
CREATE TABLE usuarios (
    id        int         GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre    text        NOT NULL,
    email     text        NOT NULL UNIQUE,
    activo    boolean     NOT NULL DEFAULT true,
    creado_en timestamptz NOT NULL DEFAULT now()
);
```

> ⚠️ **`DEFAULT` no impide `NULL`.** `DEFAULT` solo actúa cuando **omites** la
> columna. Si alguien manda `NULL` a propósito (`VALUES ('Ana', 'a@a.com', NULL)`),
> se guarda `NULL`. Para prohibirlo, `DEFAULT` + `NOT NULL` juntos.
> (Error que cometí: puse `activo boolean DEFAULT true` sin `NOT NULL`.)

**Intentos de romperla y sus errores:**

| Intento | Error |
|---|---|
| Email repetido | `duplicate key value violates unique constraint "usuarios_email_key"` |
| Sin email | `null value in column "email" ... violates not-null constraint` |
| `id` a mano | `cannot insert a non-DEFAULT value into column "id"` (por el `ALWAYS`) |

**Anatomía de un error de Postgres:**

```
ERROR:  duplicate key value violates unique constraint "usuarios_email_key"   ← qué regla se rompió
DETAIL:  Key (email)=(ana@mail.com) already exists.                          ← con qué dato
HINT:  ...                                                                    ← (a veces) cómo solucionarlo
```

- `usuarios_email_key` es el nombre que Postgres le puso al `UNIQUE` (tabla_columna_key).
- 💡 **Estos errores son los que tu API tendrá que traducir a HTTP**: un email
  repetido no es un "error 500 del servidor", es un **409 Conflict** ("ese email ya existe").
  Lo veremos en la lección 9.

**Los ids que se "pierden":** en el `DETAIL` del error de "sin email" se ve
`Failing row contains (3, Anuel, null, ...)`. Postgres **ya había gastado el id 3**
antes de comprobar las restricciones (y el 2 en el intento del email repetido).
Los ids del contador se reparten **antes** de validar, y no se devuelven. Por eso
los huecos en los ids son normales y nunca hay que usarlos para contar filas.

**Las secuencias (`usuarios_id_seq`, `pedidos_id_seq`)**

El "contador interno" de `GENERATED ... AS IDENTITY` es un objeto real de
Postgres llamado **secuencia**. Se crea solo, con el nombre `tabla_columna_seq`,
y aparece en `\d` (sin argumentos), `\ds` y `\dp`.

```sql
\ds                                   -- listar secuencias
SELECT last_value FROM pedidos_id_seq;-- último número repartido
SELECT nextval('pedidos_id_seq');     -- ⚠️ pide el SIGUIENTE (y lo gasta: crea un hueco)
```

- Una secuencia solo sabe **dar el siguiente número**. No mira la tabla, no sabe si
  el `INSERT` acabó bien. Por eso los ids que reparte para `INSERT` fallidos se pierden.
- `nextval` es **no transaccional**: un `ROLLBACK` **no** devuelve el número.
  Es a propósito: así dos inserciones a la vez nunca reciben el mismo id y no
  tienen que esperarse la una a la otra.
- La secuencia "pertenece" a la columna: si haces `DROP TABLE`, se borra con ella.

> ⚠️ **Gotcha para el trabajo (`SERIAL`):** en tablas creadas con `id SERIAL`
> (la forma antigua), el rol de la API necesita **además** permiso sobre la secuencia
> para poder hacer `INSERT`; si no: `permission denied for sequence xxx_id_seq`.
>
> ```sql
> GRANT USAGE ON SEQUENCE pedidos_id_seq TO api_curso;
> -- o todas:  GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO api_curso;
> ```
>
> Con `GENERATED ... AS IDENTITY` (la forma moderna, la nuestra) basta con el
> permiso de `INSERT` sobre la tabla.

### 3.6 Modificar una tabla que ya existe: `ALTER TABLE`

En el mundo real **no** puedes hacer `DROP TABLE` y volver a crearla: tiene datos.

```sql
ALTER TABLE usuarios ALTER COLUMN activo SET NOT NULL;      -- añadir NOT NULL
ALTER TABLE usuarios ALTER COLUMN activo DROP NOT NULL;     -- quitarlo
ALTER TABLE usuarios ALTER COLUMN activo SET DEFAULT true;  -- cambiar el default
ALTER TABLE usuarios ADD COLUMN telefono text;              -- añadir columna
ALTER TABLE usuarios DROP COLUMN telefono;                  -- borrar columna (¡y sus datos!)
ALTER TABLE usuarios RENAME COLUMN nombre TO nombre_completo;
ALTER TABLE usuarios ADD CONSTRAINT email_con_arroba CHECK (email LIKE '%@%');
```

> ⚠️ Si añades una restricción y **ya hay filas que no la cumplen**, el `ALTER`
> falla. Primero hay que arreglar los datos.

### 3.7 Fechas y horas

| Tipo | Guarda | Ejemplo |
|---|---|---|
| `date` | Solo fecha | `'2026-11-12'` |
| `time` | Solo hora | `'14:30:00'` |
| `timestamp` | Fecha + hora **sin** zona horaria | `'2026-11-12 14:30:00'` |
| `timestamptz` | Fecha + hora **con** zona horaria | `'2026-11-12 14:30:00+01'` |

**Usa siempre `timestamptz`** para "cuándo pasó algo" (creado, modificado, pedido...):

- `timestamp` guarda `14:30` sin más: ¿14:30 de Madrid? ¿de Londres? ¿UTC? No se sabe.
- `timestamptz` convierte a **UTC** al guardar y te lo muestra en tu zona al leer.
  Mismo instante para todos, estén donde estén el servidor, la API o el usuario.
- (El nombre engaña: `timestamptz` **no guarda** la zona, guarda el instante exacto en UTC.)

**Obtener la fecha/hora actual:**

```sql
SELECT now();               -- fecha y hora actual (timestamptz)
SELECT current_date;        -- solo la fecha de hoy
SHOW timezone;              -- zona horaria de la sesión (en Docker: UTC)
```

> 💡 `now()` devuelve la hora de **inicio de la transacción**: si insertas 100
> filas en la misma transacción, todas tendrán exactamente la misma hora.

**Escribir una fecha a mano:** como texto entre comillas simples en formato
**ISO** `AAAA-MM-DD HH:MM:SS`, y Postgres lo convierte:

```sql
INSERT INTO eventos (nombre, cuando) VALUES ('Reunión', '2026-11-12 09:00:00+01');
SELECT * FROM eventos WHERE cuando >= '2026-11-01';   -- comparar fechas
SELECT now() - interval '7 days';                     -- hace una semana
```

**Borrar una tabla:** `DROP TABLE nombre;` ⚠️ Borra la tabla **y todos sus
datos**, sin papelera y sin preguntar.

### 3.8 CRUD: las 4 operaciones que hará tu API

| CRUD | SQL | Endpoint típico |
|---|---|---|
| **C**reate | `INSERT` | `POST /usuarios` |
| **R**ead | `SELECT` | `GET /usuarios`, `GET /usuarios/4` |
| **U**pdate | `UPDATE` | `PUT` / `PATCH /usuarios/4` |
| **D**elete | `DELETE` | `DELETE /usuarios/4` |

**INSERT de varias filas a la vez:**

```sql
INSERT INTO usuarios (nombre, email) VALUES
    ('Luis', 'luis@mail.com'),
    ('Marta', 'marta@mail.com');
```

**SELECT:**

```sql
SELECT * FROM usuarios;                                  -- todo (evítalo en la API: pide solo lo que necesites)
SELECT id, nombre FROM usuarios;                         -- solo algunas columnas
SELECT * FROM usuarios WHERE id = 4;                     -- filtrar
SELECT * FROM usuarios WHERE activo AND nombre LIKE 'A%';-- varias condiciones; LIKE: % = "lo que sea"
SELECT * FROM usuarios WHERE nombre ILIKE '%ana%';       -- ILIKE = LIKE sin distinguir mayúsculas
SELECT * FROM usuarios ORDER BY creado_en DESC;          -- ordenar (DESC = de mayor a menor)
SELECT * FROM usuarios ORDER BY id LIMIT 10 OFFSET 20;   -- paginar: 10 filas saltándose las 20 primeras
SELECT count(*) FROM usuarios;                           -- contar
```

> ⚠️ **Sin `ORDER BY`, el orden de las filas NO está garantizado.** Hoy pueden salir
> ordenadas por casualidad y mañana no. Si el orden importa (paginación), ponlo siempre.

**UPDATE:**

```sql
UPDATE usuarios SET activo = false WHERE id = 4;
UPDATE usuarios SET nombre = 'Ana María', email = 'anamaria@mail.com' WHERE id = 1;
```

**DELETE:**

```sql
DELETE FROM usuarios WHERE id = 4;
```

> 🚨 **`UPDATE` y `DELETE` sin `WHERE` afectan a TODAS las filas.**
> `DELETE FROM usuarios;` borra todos los usuarios, sin preguntar.
> Respuesta de Postgres: `DELETE 2` / `UPDATE 1` → **cuántas filas** ha tocado.
> Si esperabas 1 y pone 5000, algo va mal.

**`RETURNING`: que el `INSERT`/`UPDATE`/`DELETE` te devuelva las filas afectadas**

```sql
INSERT INTO usuarios (nombre, email) VALUES ('Eva', 'eva@mail.com') RETURNING *;
UPDATE usuarios SET activo = false WHERE id = 5 RETURNING id, activo;
DELETE FROM usuarios WHERE id = 5 RETURNING *;
```

💡 **Clave para la API:** un `POST /usuarios` debe responder con el usuario creado,
**incluido su `id` y `creado_en`**, que los ha generado Postgres. Con `RETURNING`
lo obtienes en la misma consulta, sin hacer un `SELECT` después.

### 3.9 Transacciones: la red de seguridad

```sql
BEGIN;                                   -- empieza una transacción
UPDATE usuarios SET activo = false;      -- ups, sin WHERE → "UPDATE 3"
SELECT * FROM usuarios;                  -- compruebas el desastre (solo lo ves tú)
ROLLBACK;                                -- deshace TODO desde el BEGIN
-- o COMMIT;                             -- confirma y guarda de verdad
```

- Mientras no hagas `COMMIT`, los cambios **solo los ves tú**; el resto de
  conexiones (y tu API) siguen viendo los datos de antes.
- Si algo falla dentro de la transacción, Postgres la marca como rota y hay que hacer `ROLLBACK`.
- En `psql`, sin `BEGIN`, cada sentencia se confirma sola al momento (*autocommit*).
- También sirve para que **varias operaciones se hagan todas o ninguna** (p. ej.
  restar dinero de una cuenta y sumarlo en otra).

**Lo que se vio en el ejercicio:**

```
curso=# BEGIN;
curso=*# DELETE FROM usuarios;     ← el * del prompt = estás DENTRO de una transacción abierta
DELETE 4
curso=*# ROLLBACK;
curso=#                            ← sin * = transacción cerrada
```

- Luis y Marta, insertados en el **mismo** `INSERT`, tienen **exactamente** el mismo
  `creado_en`: `now()` da la hora de inicio de la transacción, no la de cada fila.
- `ILIKE 'a%'` y `ILIKE 'A%'` dan lo mismo (no distingue mayúsculas). Con `LIKE`, `'a%'` no encontraría a "Ana".
- `ORDER BY name` → `column "name" does not exist`: el `^` del error apunta justo a la palabra mal escrita.
- En `psql` el **TAB** autocompleta palabras de SQL, nombres de tablas y columnas.

**Experimento con dos terminales:** A hace `BEGIN; DELETE FROM usuarios;` (sin
confirmar) y B hace `SELECT * FROM usuarios;` → B ve **las 4 filas**. Lo no
confirmado es invisible para los demás. (Trampa 2: B necesita `SELECT` sobre
`usuarios`; sin `GRANT` le habría dado `permission denied`.)

### 3.10 Cómo lo hace Postgres por dentro: MVCC

Modelo intuitivo (pero **incorrecto**): "tras el `BEGIN` los cambios se guardan
en RAM en una copia, `ROLLBACK` los tira y al confirmar se escriben al disco".

Cómo funciona de verdad (**MVCC**, *Multi-Version Concurrency Control*):

1. Cada transacción tiene un **número** (id de transacción).
2. Un `DELETE` **no borra** la fila: le pone una marca *"borrada por la transacción 750"*.
   Un `UPDATE` no modifica: marca la fila vieja como borrada y **crea una versión nueva**.
3. Esos cambios se escriben como cualquier otro (a memoria compartida y al **WAL**,
   el diario en disco). **No** esperan al final.
4. Cada consulta mira una **foto** (*snapshot*) de qué transacciones estaban
   confirmadas cuando empezó. La marca "borrada por la 750" solo cuenta si la 750
   está **confirmada**. Para B no lo estaba → seguía viendo las filas.
5. **`COMMIT`** (no `BEGIN`) apunta "la 750 está confirmada" → desde ese momento las marcas cuentan para todos.
   **`ROLLBACK`** apunta "la 750 se abortó" → sus marcas se ignoran para siempre. No hay que deshacer nada,
   por eso `ROLLBACK` es instantáneo aunque hayas borrado un millón de filas.
6. Más tarde, un proceso de limpieza (**`VACUUM`**, automático) recoge las versiones
   que ya nadie puede ver y libera el espacio.

> 💡 Consecuencia práctica: **los lectores no bloquean a los escritores ni al
> revés**. Tu API puede estar haciendo `SELECT` mientras otro proceso hace `UPDATE`
> sin esperarse. Lo que sí se bloquea: **dos escrituras sobre la misma fila**;
> la segunda espera a que la primera haga `COMMIT`/`ROLLBACK`.
>
> ⚠️ Por eso una transacción olvidada abierta (`curso=*#`) en un servidor real es
> peligrosa: bloquea a cualquiera que quiera modificar esas filas.

> 💡 **Hábito para el trabajo:** antes de un `UPDATE`/`DELETE` a mano en un
> servidor con datos reales: `BEGIN;` → la sentencia → mira el número de filas →
> `COMMIT;` solo si cuadra.

---

## Lección 4 — Relaciones: claves foráneas, JOINs, índices

### 4.1 Por qué separar en varias tablas

Mala idea: guardar el autor dentro de cada libro.

```
 titulo            | autor_nombre | autor_pais
-------------------+--------------+-----------
 Cien años...      | G. Márquez   | Colombia
 El amor en...     | G. Marquez   | Colombia     ← ¿es el mismo? alguien lo escribió sin tilde
 Crónica de...     | G. Márquez   | Colmbia      ← errata: ahora hay 3 versiones del mismo dato
```

Buena idea: cada cosa en **su tabla**, y se **referencian por id**:

```
autores                         libros
 id | nombre     | pais          id | titulo        | autor_id
----+------------+---------     ----+---------------+----------
  1 | G. Márquez | Colombia       1 | Cien años...  |        1   ─┐
                                  2 | El amor en... |        1   ─┼─▶ todos apuntan al autor 1
                                  3 | Crónica de... |        1   ─┘
```

- El dato del autor está en **un solo sitio**: si lo corriges, se corrige para todos sus libros.
- Esto es una relación **uno a muchos (1:N)**: un autor tiene muchos libros; un libro, un autor.
- La columna `autor_id` va en el lado de los **"muchos"** (`libros`).

### 4.2 Clave foránea (FOREIGN KEY)

Una **clave foránea** es una columna que **apunta a la clave primaria de otra
tabla**, y Postgres **garantiza** que lo que apunta existe.

```sql
CREATE TABLE autores (
    id     int  GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre text NOT NULL
);

CREATE TABLE libros (
    id       int  GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    titulo   text NOT NULL,
    autor_id int  NOT NULL REFERENCES autores (id)
    --                     ^^^^^^^^^^^^^^^^^^^^^^^ clave foránea
);
```

- El **tipo** de la columna tiene que coincidir con el de la clave primaria a la que apunta (`int` → `int`).
- Convención de nombres: `<tabla_en_singular>_id` → `autor_id`, `usuario_id`.
- `NOT NULL` → todo libro **tiene** que tener autor. Sin él, el libro podría quedar "huérfano" (con `autor_id` a `NULL`).

**Qué impide:**

| Intento | Resultado |
|---|---|
| Insertar un libro con `autor_id = 999` (no existe) | `ERROR: insert or update on table "libros" violates foreign key constraint` |
| Borrar un autor que tiene libros | `ERROR: update or delete on table "autores" violates foreign key constraint ... is still referenced` |

**¿Qué hacer al borrar el "padre"?** Se decide con `ON DELETE`:

```sql
autor_id int NOT NULL REFERENCES autores (id) ON DELETE CASCADE
```

| Opción | Al borrar el autor... | Cuándo usarla |
|---|---|---|
| *(nada)* / `RESTRICT` | Error si tiene libros | **Por defecto y lo más seguro** |
| `CASCADE` | Se borran **también** todos sus libros | Cuando los hijos no tienen sentido sin el padre (líneas de un pedido) |
| `SET NULL` | Sus libros quedan con `autor_id = NULL` | Cuando el hijo puede vivir sin padre (requiere que la columna admita `NULL`) |

> ⚠️ `CASCADE` es cómodo y peligroso: un `DELETE` de una fila puede borrar
> miles en otras tablas sin avisar. En el trabajo, antes de borrar algo,
> mira con `\d tabla` si otras tablas apuntan a ella (sección *Referenced by*).

### 4.3 JOIN: consultar varias tablas a la vez

Un `JOIN` **une filas de dos tablas** según una condición (normalmente: la
clave foránea de una = la clave primaria de la otra).

```sql
SELECT libros.titulo, autores.nombre
FROM libros
JOIN autores ON libros.autor_id = autores.id;
--           ^^ la condición para emparejar filas
```

**Alias** para escribir menos (muy habitual):

```sql
SELECT l.titulo, a.nombre
FROM libros l
JOIN autores a ON l.autor_id = a.id
WHERE a.nombre = 'G. Márquez'
ORDER BY l.titulo;
```

> ⚠️ Si dos tablas tienen una columna con el **mismo nombre** (las dos tienen
> `id`), hay que decir de cuál: `l.id` o `a.id`. Si no:
> `ERROR: column reference "id" is ambiguous`.

**Tipos de JOIN** (los dos que usarás el 99 % del tiempo):

| JOIN | Devuelve | Ejemplo |
|---|---|---|
| `JOIN` (= `INNER JOIN`) | Solo las filas que **tienen pareja** en las dos tablas | Libros con su autor |
| `LEFT JOIN` | **Todas** las filas de la tabla de la izquierda, tengan pareja o no. Si no tienen, las columnas de la derecha salen `NULL` | Todos los autores, **también los que no tienen libros** |

```
autores: 1 Márquez, 2 Borges (sin libros)

JOIN       → solo Márquez (con cada uno de sus libros)
LEFT JOIN  → Márquez (con sus libros) + Borges con titulo = NULL
```

Truco clásico — "autores **sin** libros":

```sql
SELECT a.nombre
FROM autores a
LEFT JOIN libros l ON l.autor_id = a.id
WHERE l.id IS NULL;
```

### 4.4 Agrupar: `GROUP BY`

Para preguntas del tipo "**cuántos** / **cuánto** **por** cada X":

```sql
SELECT a.nombre, count(l.id) AS num_libros
FROM autores a
LEFT JOIN libros l ON l.autor_id = a.id
GROUP BY a.id, a.nombre
ORDER BY num_libros DESC;
```

- `GROUP BY` junta las filas que comparten valor → **una fila por grupo**.
- Funciones de agregado: `count()`, `sum()`, `avg()`, `min()`, `max()`.
- Regla: toda columna del `SELECT` que **no** esté dentro de una función de agregado
  tiene que estar en el `GROUP BY`. Si no: `ERROR: column "..." must appear in the GROUP BY clause`.
- `AS num_libros` → pone nombre a la columna del resultado (será la clave del JSON en la API).
- `count(l.id)` y no `count(*)`: con `LEFT JOIN`, `count(*)` contaría 1 para un autor
  sin libros (la fila con `NULL`); `count(l.id)` no cuenta los `NULL` → 0. ✔️
- Para filtrar **grupos** (no filas) se usa `HAVING`: `... GROUP BY ... HAVING count(l.id) > 5`.

### 4.5 Ejercicio del curso: `usuarios` ← `pedidos`

```sql
CREATE TABLE pedidos (
    id         int           GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id int           NOT NULL REFERENCES usuarios (id),
    producto   text          NOT NULL,
    importe    numeric(10,2) NOT NULL CHECK (importe >= 0),
    creado_en  timestamptz   NOT NULL DEFAULT now()
);
```

**Errores y lo que enseñan:**

| SQL | Error | Lección |
|---|---|---|
| Pedido de `usuario_id = 999` | `violates foreign key constraint "pedidos_usuario_id_fkey"` / `Key (usuario_id)=(999) is not present in table "usuarios"` | La FK impide apuntar a algo que no existe |
| `importe = -5` | `violates check constraint "pedidos_importe_check"` | El `CHECK` funciona |
| Borrar a Ana (tiene pedidos) | `... is still referenced from table "pedidos"` | Sin `ON DELETE`, Postgres protege a los hijos |
| `JOIN pedidos p;` (sin `ON`) | `syntax error at or near ";"` | Un `JOIN` necesita su condición `ON` |
| `LEFT JOIN pedidos p WHERE u.id = ...` | `syntax error at or near "WHERE"` | La condición de emparejar va en `ON`, no en `WHERE` |
| `GROUP BY` olvidado con `count()` | `column "u.nombre" must appear in the GROUP BY clause` | Columnas sin agregar → al `GROUP BY` |

**El prompt `curso=!#`:** tras un error **dentro** de una transacción, el prompt
pasa de `*` a `!` = **transacción rota**. Todo lo que escribas dará
`current transaction is aborted, commands ignored until end of transaction block`.
Única salida: `ROLLBACK;`.

```
curso=#    sin transacción
curso=*#   transacción abierta, todo bien
curso=!#   transacción abierta y ROTA → ROLLBACK
```

**`\d usuarios` → `Referenced by:`** aparece cuando otra tabla tiene una FK
apuntando a esta. Antes de borrar filas o la tabla, mira esto.

**`ON` vs `WHERE`:**
- `ON` → **cómo emparejar** las filas de las dos tablas.
- `WHERE` → **qué filas quedan** después de unirlas.
- En el truco de "usuarios sin pedidos", el `WHERE p.id IS NULL` va **después**
  del `LEFT JOIN`: se quedan las filas donde no hubo pareja.

**`GROUP BY u.id` vs `GROUP BY u.nombre`** (los dos funcionaron):
- `GROUP BY u.id` ✅ → como `id` es la clave primaria, Postgres sabe que cada id
  tiene un único nombre, así que deja usar `u.nombre` en el `SELECT`.
- `GROUP BY u.nombre` ❌ peligroso → si hay **dos usuarios** llamados "Ana",
  los mezcla en **un solo grupo** y suma sus pedidos. Funciona hoy por casualidad.
  **Agrupa siempre por el id.**

**`SELECT *` con JOIN:** el resultado tiene **dos columnas `id`** y **dos
`creado_en`**. En la API, al convertirlo a JSON, una pisaría a la otra.
**Con JOIN, nombra siempre las columnas:** `u.id AS usuario_id, p.id AS pedido_id`.

**`sum()` de nada es `NULL`, no `0`** → `coalesce`:

```sql
SELECT u.nombre,
       count(p.id)                 AS num_pedidos,
       coalesce(sum(p.importe), 0) AS total_gastado
FROM usuarios u
LEFT JOIN pedidos p ON u.id = p.usuario_id
GROUP BY u.id, u.nombre
ORDER BY total_gastado DESC;
```

- Sin pedidos, `sum(p.importe)` suma cero filas → `NULL`. (`count` en cambio da `0`.)
- `coalesce(a, b, ...)` → devuelve **el primero que no sea `NULL`**.
- Sin `coalesce`, la API mandaría `"total_gastado": null` y el frontend pintaría "Has gastado null €".
- Además, en `ORDER BY ... DESC` los `NULL` salen **los primeros**: Marta y
  Anuel aparecerían arriba del ranking de gasto. (Se puede controlar con `NULLS LAST`.)

**Buffer de `psql`:** si el prompt se queda en `curso-#` es que hay texto a medias
esperando un `;`. Para descartarlo: **Ctrl+C** o `\r` (*reset*). Ver qué hay: `\p`.

### 4.6 Índices

Sin índice, para encontrar `WHERE usuario_id = 5` Postgres lee **la tabla entera**,
fila a fila (*Sequential Scan*). Con 4 filas no importa; con 10 millones, sí.

Un **índice** es como el índice alfabético de un libro: una estructura aparte
(un árbol **B-tree**, ordenado) que dice "el valor 5 está en estas filas", sin
leerlo todo.

```sql
CREATE INDEX nombre_indice ON tabla (columna);
CREATE INDEX pedidos_usuario_id_idx ON pedidos (usuario_id);   -- convención: tabla_columna_idx
DROP INDEX nombre_indice;
```

**Cuáles crea Postgres solo y cuáles no:**

| Restricción | ¿Crea índice? |
|---|---|
| `PRIMARY KEY` | ✅ Sí (`usuarios_pkey`) |
| `UNIQUE` | ✅ Sí (`usuarios_email_key`); lo necesita para comprobar duplicados rápido |
| `REFERENCES` (clave foránea) | ❌ **NO**. Hay que crearlo a mano |

> 💡 **Regla práctica: crea un índice en cada columna de clave foránea.** Se usan
> en casi todos los `JOIN` y `WHERE` ("pedidos del usuario 5"), y además Postgres
> los necesita para comprobar rápido si puede borrar un usuario (¿tiene pedidos?).

**Qué columnas indexar:** las que aparecen mucho en `WHERE`, `JOIN ... ON` y
`ORDER BY`. **No** indexes todo: cada índice ocupa espacio y **hace más lentos
los `INSERT`/`UPDATE`/`DELETE`** (hay que actualizar la tabla y todos sus índices).

**`EXPLAIN`: ¿cómo va a ejecutar Postgres mi consulta?**

```sql
EXPLAIN SELECT * FROM pedidos WHERE usuario_id = 5;
--  Seq Scan on pedidos ...                  ← lee toda la tabla
--  Index Scan using pedidos_usuario_id_idx  ← usa el índice
EXPLAIN ANALYZE SELECT ...;                  -- la ejecuta de verdad y da tiempos reales
```

> ⚠️ En tablas **pequeñas** Postgres hace `Seq Scan` **aunque haya índice**: leer
> 3 filas seguidas es más rápido que consultar un índice y luego saltar a la tabla.
> El *planificador* decide según el tamaño de la tabla. Que salga `Seq Scan` en tu
> tabla de prueba **no** significa que el índice esté mal.

**Lo que pasó en el curso:**

```
-- ANTES del índice
Seq Scan on pedidos  (cost=0.00..21.00 rows=4 width=64)
-- DESPUÉS del índice
Seq Scan on pedidos  (cost=0.00..1.04 rows=1 width=64)
```

Cómo leer la línea del plan:
- `Seq Scan` / `Index Scan` → **cómo** va a leer. **Esto es lo importante**, y no cambió: el índice **no se usó**.
- `cost=inicio..total` → coste **estimado** en unidades inventadas por Postgres (no son ms). Solo sirve para comparar planes.
- `rows=` → cuántas filas **cree que va a devolver** (una estimación), **no** cuántas ha mirado.
- `width=` → tamaño medio estimado de cada fila en bytes.

¿Por qué cambiaron `cost` y `rows` si el plan es el mismo? Porque son
**estimaciones**, y dependen de las **estadísticas** que Postgres tiene de la
tabla. Antes, la tabla era recién creada y no tenía estadísticas: Postgres
suponía una tabla de tamaño "por defecto". `CREATE INDEX` recorre la tabla
entera y, de paso, actualiza las estadísticas: "esta tabla tiene 3 filas en 1
página". Con esos datos reales, la estimación baja. (Las estadísticas también
se actualizan con `ANALYZE pedidos;` y con el *autovacuum*.)

Para **ver** el índice en acción en una tabla pequeña (solo para aprender, **nunca** en producción):

```sql
SET enable_seqscan = off;     -- "prohíbe" el Seq Scan en esta sesión
EXPLAIN SELECT * FROM pedidos WHERE usuario_id = 5;
RESET enable_seqscan;
```

**¿Por qué no indexar todas las columnas?**
1. **Espacio**: cada índice es una estructura aparte que ocupa disco y memoria.
2. **Escrituras más lentas** (el motivo principal): cada `INSERT`/`UPDATE`/`DELETE`
   tiene que actualizar la tabla **y cada uno de sus índices**. 10 índices = 11 escrituras.
3. Un índice que no se usa en ninguna consulta es coste sin beneficio.

**Nombres de índices:** son únicos **por schema**, no por tabla. Por eso la
convención incluye la tabla: `pedidos_usuario_id_idx`. Si se llamara
`usuario_id_idx` y mañana `facturas` también tuviera `usuario_id`, chocarían.

```sql
ALTER INDEX usuario_id_idx RENAME TO pedidos_usuario_id_idx;
```

---

## Lección 5 — Proyecto Python: entorno virtual, dependencias, variables de entorno

### 5.1 Entorno virtual (`venv`)

**Problema:** si instalas librerías con `pip` "a lo global", todos tus proyectos
comparten las mismas versiones. El proyecto A necesita FastAPI 0.100 y el B la
0.115 → conflicto. Además, Ubuntu 24.04 directamente **no te deja** instalar
con `pip` en el Python del sistema (`error: externally-managed-environment`).

**Solución:** un **entorno virtual** = una carpeta con **su propio** Python y
**sus propias** librerías, solo para este proyecto.

```bash
python3 -m venv .venv          # crea el entorno en la carpeta .venv
source .venv/bin/activate      # lo ACTIVA en esta terminal → el prompt empieza por (.venv)
which python                   # comprobar: debe apuntar a .../curso-servidores/.venv/bin/python
deactivate                     # salir del entorno
```

- `python3 -m venv` → "ejecuta el módulo `venv` de Python".
- `.venv` es el nombre de la carpeta (convención; el punto la oculta en `ls`).
- **Hay que activarlo en cada terminal nueva.** Si `pip install` o `python` se
  comportan raro, lo primero: ¿sale `(.venv)` en el prompt?
- La carpeta `.venv` **no se sube a git** (pesa mucho y es específica de tu máquina).
  Se sube la **lista** de dependencias y cada uno se crea su entorno.

### 5.2 Dependencias

Con el entorno activado:

```bash
pip install "fastapi[standard]" "psycopg[binary,pool]"
```

| Paquete | Qué es |
|---|---|
| `fastapi` | El framework para crear la API |
| `[standard]` | "Extras": añade `uvicorn` (el **servidor** que ejecuta la API), el comando `fastapi`, etc. |
| `psycopg` | El **driver**: la librería que habla el protocolo de Postgres desde Python (versión 3) |
| `[binary]` | Trae ya compilada la parte en C (si no, necesitarías tener instalado `libpq`) |
| `[pool]` | *Pool* de conexiones (lección 7) |

> ⚠️ Las comillas en `"fastapi[standard]"` son necesarias: sin ellas, bash
> interpreta los corchetes `[]` como un patrón de ficheros.
>
> ⚠️ `psycopg2` (con 2) es la versión **antigua**, todavía muy extendida. Si
> en el trabajo veis `import psycopg2`, es la misma idea con otra API. Nosotros: `psycopg` (3).

**Guardar la lista de dependencias** para que otro (o tú en el portátil) pueda reproducir el entorno:

```bash
pip freeze > requirements.txt          # vuelca TODAS las librerías instaladas con su versión exacta
pip install -r requirements.txt        # instalar desde la lista (en otra máquina)
```

### 5.3 Variables de entorno y `.env`: **nunca** contraseñas en el código

❌ Mal:

```python
conn = psycopg.connect("postgresql://api_curso:api1234@localhost:5432/curso")
```

- En cuanto haces `git push`, **la contraseña está en GitHub**. Y aunque la borres
  después, sigue en el **historial** de git. Hay bots que escanean GitHub buscando contraseñas.
- Cada entorno (tu PC, pruebas, producción) usa una BD distinta → tendrías que tocar el código.

✅ Bien: la configuración vive en **variables de entorno**, y el código las lee.

**Variable de entorno** = un valor con nombre que el sistema operativo le pasa
a cada programa que arranca (como el `-e` de Docker, que ya usamos):

```bash
export DATABASE_URL="postgresql://..."   # definirla en esta terminal
echo $DATABASE_URL                       # verla
```

```python
import os
url = os.environ["DATABASE_URL"]         # leerla desde Python (error si no existe)
url = os.getenv("DATABASE_URL")          # igual, pero devuelve None si no existe
```

**Fichero `.env`:** para no tener que hacer `export` cada vez, se escriben en un fichero:

```bash
# .env
DATABASE_URL=postgresql://usuario:contraseña@localhost:5432/curso
```

y una librería (o FastAPI, lo veremos) lo carga al arrancar.

**`.gitignore`:** fichero que le dice a git **qué no subir nunca**:

```gitignore
.venv/
.env
__pycache__/
```

> 💡 Convención: se sube un **`.env.example`** con las mismas claves pero valores
> de mentira. Así quien clone el repo sabe qué variables tiene que rellenar.
>
> ```bash
> # .env.example
> DATABASE_URL=postgresql://USUARIO:CONTRASEÑA@localhost:5432/curso
> ```

### 5.4 Primera conexión desde Python con `psycopg`

Piezas (para montar tu script):

```python
import psycopg

with psycopg.connect(url) as conn:          # abre la conexión (y la cierra al salir del with)
    with conn.cursor() as cur:              # el "cursor" es por donde mandas SQL y recibes filas
        cur.execute("SELECT ...")           # manda el SQL
        fila = cur.fetchone()               # recoge UNA fila → tupla, p. ej. (1, 'Ana')
        filas = cur.fetchall()              # recoge TODAS → lista de tuplas
```

- `with` → se asegura de cerrar la conexión aunque haya un error.
- Al salir del `with` de la conexión, psycopg hace **`COMMIT`** si todo fue bien
  y **`ROLLBACK`** si hubo una excepción. Es decir: en Python, **cada conexión
  trabaja dentro de una transacción** (lo contrario que `psql`, que hace autocommit).
  Si haces un `INSERT` y no se confirma, no se guarda.

### 5.5 Lecciones de la revisión de código

**`os.getenv` vs `os.environ[...]` → falla pronto y claro (*fail fast*):**

```python
url = os.getenv("DATABASE_URL")     # si falta → None → psycopg intenta conectar "por defecto"
                                    #   (socket local, usuario de Linux...) → error confuso y lejos de la causa
url = os.environ["DATABASE_URL"]    # si falta → KeyError: 'DATABASE_URL' → sabes al instante qué pasa
```

Para configuración **obligatoria**, que reviente en la primera línea con un
error que diga exactamente qué falta. `getenv` es para cosas **opcionales**
con valor por defecto: `os.getenv("PUERTO", "8000")`.

**Ejemplo real del curso** (ejecutando el script con el botón ▶ del editor, sin cargar el `.env`):

```
Traceback (most recent call last):
  File ".../prueba_conexion.py", line 6, in <module>          ← 2º) la ÚLTIMA línea de TU código: aquí empezó
    with psycopg.connect(url) as conn:
  File ".../site-packages/psycopg/connection.py", line 97 ...  ← código de la librería (lo saltas)
  ...
  File ".../site-packages/psycopg/conninfo.py", line 101 ...
    return pq.Conninfo.parse(conninfo.encode())
AttributeError: 'NoneType' object has no attribute 'encode'    ← 1º) EL ERROR: se lee primero
```

**Cómo leer un *traceback* de Python:**
1. Empieza por **abajo**: la última línea es el error (`tipo: mensaje`).
2. Sube hasta la **última línea que sea de tu código** (no de `site-packages/`, que
   son librerías). Ahí está lo que tú hiciste mal; el resto es "por dónde pasó".
3. Traduce: `'NoneType' object has no attribute 'encode'` = "alguien recibió
   `None` donde esperaba un texto". ¿Qué le pasé yo a `connect`? `url`. ¿De dónde sale? `getenv` → `None`.

El error salta **4 llamadas más adentro**, en código que no es tuyo, y no
menciona `DATABASE_URL` por ningún lado. Eso es justo lo que evita `os.environ[...]`.

**¿Por qué `url` era `None`?** Las variables de entorno son **de cada proceso**:
un programa recibe una **copia** de las de quien lo lanza. Hacer `source .env`
en una terminal solo afecta a **esa** terminal y a lo que lances **desde ella**.
El botón ▶ del editor lanza Python desde otro proceso, que nunca vio el `.env`.
(En la lección 7 haremos que la propia app cargue el `.env` sola.)

**El usuario de la API solo ve lo que se le ha dado:** `api_curso` tiene
`SELECT` en `usuarios`, pero **no** en `pedidos` → `permission denied for table pedidos`.
Lo del `\dp` de la lección 2 aplica igual desde Python.

```
psycopg.errors.InsufficientPrivilege: permission denied for table pedidos
```

**psycopg convierte cada error de Postgres en una excepción de Python con nombre propio:**

| Error en `psql` | Excepción en Python |
|---|---|
| `permission denied for table ...` | `psycopg.errors.InsufficientPrivilege` |
| `duplicate key value violates unique constraint` | `psycopg.errors.UniqueViolation` |
| `violates foreign key constraint` | `psycopg.errors.ForeignKeyViolation` |
| `violates not-null constraint` | `psycopg.errors.NotNullViolation` |
| `violates check constraint` | `psycopg.errors.CheckViolation` |

Así se pueden **capturar por tipo** con `try/except` y responder distinto a
cada uno (p. ej. `UniqueViolation` → HTTP 409 "ese email ya existe"). Lección 9.

Solución aplicada en el curso: `GRANT SELECT ON pedidos TO api_curso;` (como `postgres`).
Solo `r`: la API de momento solo **lee** pedidos → mínimo privilegio.

**Por qué `SELECT *` + desempaquetado se rompe:**

```python
cur.execute("SELECT * FROM pedidos")              # devuelve 5 columnas
for index, id, producto, precio in filas:         # pero aquí esperas 4
# ValueError: too many values to unpack (expected 4)
```

- *too many values to unpack (expected 4)* = la tupla trae **más** valores que variables.
  (*not enough values* = trae **menos**.)
- Con `SELECT *` el número de columnas lo decide **la tabla**, no tu código: si
  alguien añade una columna, el código que funcionaba se rompe. Con las columnas
  escritas en el `SELECT`, **tú** controlas cuántas y en qué orden.

**Nombres de variables:**
- Que digan **lo que son**: `pedido_id`, `usuario_id`, `importe` (como la columna),
  no `index`, `id`, `precio`.
- No uses `id` como variable: **tapa** la función `id()` de Python (igual con
  `list`, `type`, `input`, `sum`...).

### 5.6 Tipos de Postgres → tipos de Python

Resultado de `fetchall()` sobre `pedidos`:

```python
[(1, 1, 'Iphone 18 pro max', Decimal('1883.95'),
  datetime.datetime(2026, 11, 12, 9, 57, 44, 206571, tzinfo=zoneinfo.ZoneInfo(key='Etc/UTC'))), ...]
```

- `fetchall()` → **lista** de filas; cada fila es una **tupla**, con las columnas en el orden del `SELECT`.
- psycopg **convierte los tipos** automáticamente:

| Postgres | Python | Ojo |
|---|---|---|
| `int` | `int` | |
| `text` | `str` | |
| `boolean` | `bool` | |
| `NULL` | `None` | |
| `numeric(10,2)` | `Decimal('1883.95')` | **No** `float`: `Decimal` es exacto, como `numeric`. Con `float`, `0.1 + 0.2 = 0.30000000000000004` |
| `timestamptz` | `datetime` **con zona** (`tzinfo=UTC`) | Un *datetime "aware"*: sabe en qué zona está. Compararlo con uno sin zona da error |

> 💡 Al devolverlo en la API, FastAPI convierte esto a JSON: `Decimal` → número
> (o texto, según configuración), `datetime` → texto ISO `"2026-11-12T09:57:44.206571Z"`.
> El JSON no tiene tipo "fecha": las fechas viajan como texto.

**`.env` / `.env.example` / `.gitignore`:**
- `.env.example` con un **ejemplo del formato**, no vacío: quien clone el repo tiene que saber qué poner.
- Añadir `__pycache__/` al `.gitignore` **antes** de que aparezca (Python lo crea al importar módulos).
- Comprobar que git ignora un fichero: `git check-ignore -v .env`.

---

## Lección 6 — FastAPI: primer endpoint, rutas, Swagger

### 6.1 HTTP en 5 minutos

Una API web es un programa que **recibe peticiones HTTP** y **devuelve respuestas HTTP**.

**Petición** (lo que manda el cliente):

```
GET /usuarios/4?incluir_pedidos=true HTTP/1.1
└┬┘ └─────┬───┘└────────┬──────────┘
método   ruta     query string (parámetros opcionales tras el ?)
```

**Respuesta** (lo que devuelve tu API):

```
HTTP/1.1 200 OK                      ← código de estado
Content-Type: application/json       ← cabecera: "te mando JSON"

{"id": 4, "nombre": "Anuel"}         ← cuerpo (body)
```

**Métodos** (el "verbo": qué quieres hacer):

| Método | Para | SQL que suele ejecutar |
|---|---|---|
| `GET` | Leer | `SELECT` |
| `POST` | Crear | `INSERT` |
| `PUT` / `PATCH` | Reemplazar / modificar parte | `UPDATE` |
| `DELETE` | Borrar | `DELETE` |

**Códigos de estado** (se agrupan por la primera cifra):

| Código | Significa | Ejemplo |
|---|---|---|
| `200 OK` | Todo bien | `GET` que encuentra lo pedido |
| `201 Created` | Creado | `POST` correcto |
| `204 No Content` | Bien, sin nada que devolver | `DELETE` correcto |
| `400 Bad Request` | Petición mal hecha | |
| `404 Not Found` | No existe | `GET /usuarios/999` |
| `409 Conflict` | Choca con lo que hay | Email repetido |
| `422 Unprocessable Content` | Datos con formato inválido | `/usuarios/abc` cuando se espera un número |
| `500 Internal Server Error` | **Tu código ha fallado** | Una excepción sin capturar |

> 💡 **4xx = la culpa es del cliente** (pidió algo mal). **5xx = la culpa es
> del servidor** (tu código). Un buen API casi nunca devuelve 500: los errores
> previsibles (no existe, repetido...) se convierten en un 4xx con un mensaje claro.

**JSON:** el formato de texto en que viajan los datos. Se parece mucho a un `dict` de Python:

```json
{"id": 4, "nombre": "Anuel", "activo": true, "email": null, "pedidos": [1, 2]}
```

(`true`/`false`/`null` en minúscula, comillas **dobles** siempre.)

### 6.2 La app mínima

```python
from fastapi import FastAPI

app = FastAPI()                 # la aplicación; el servidor la busca por este nombre

@app.get("/")                   # "cuando llegue un GET a la ruta /, ejecuta esta función"
def raiz():
    return {"mensaje": "hola"}  # devuelves un dict → FastAPI lo convierte a JSON (200 OK)
```

- `@app.get("/ruta")` es un **decorador**: "registra" la función como la que atiende
  esa combinación de **método + ruta**. A esa función se le llama ***endpoint***
  (o *path operation* en la documentación de FastAPI).
- Hay uno por método: `@app.post`, `@app.put`, `@app.patch`, `@app.delete`.
- El nombre de la función no importa para la URL (solo sale en la documentación).

### 6.3 Arrancar el servidor

```bash
fastapi dev main.py
```

- Arranca **uvicorn** (el servidor) en `http://127.0.0.1:8000`.
- `dev` = modo desarrollo: **se recarga solo** al guardar cambios en el código.
  (En producción se usa `fastapi run`, sin recarga.)
- La terminal se queda "ocupada" mostrando cada petición que llega. **Ctrl+C** para pararlo.
- `main.py` no es un nombre mágico, pero es la convención.

**Probarlo:**
- En el navegador: `http://localhost:8000/` (el navegador siempre hace `GET`).
- Desde otra terminal con `curl`:

```bash
curl http://localhost:8000/
curl -i http://localhost:8000/       # -i: muestra también código de estado y cabeceras
```

> ⚠️ **URLs con `&` → siempre entre comillas.** Para bash, `&` significa
> "lanza esto en segundo plano":
>
> ```bash
> curl -i http://localhost:8000/sumar?a=5&b=3
> # bash lo entiende como DOS comandos:
> #   1) curl -i http://localhost:8000/sumar?a=5   & ← en segundo plano → [1] 11652 (nº de trabajo, PID)
> #   2) b=3                                          ← crea una variable de bash llamada b
> # resultado: {"resultado":5}  (b no llegó nunca a la API)
> ```
>
> Con `"..."`, bash pasa la URL entera a `curl` como un solo texto. Lo mismo
> pasa con `?`, `*` y `[]`, que también son especiales para bash.
>
> (Que el JSON salga pegado al prompt es normal: la respuesta no acaba en salto
> de línea. Si molesta: `curl -i ...; echo`.)

### 6.4 Parámetros

**Parámetro de ruta (*path parameter*):** forma parte de la URL. Para identificar **un recurso concreto**.

```python
@app.get("/libros/{libro_id}")
def leer_libro(libro_id: int):          # el nombre tiene que coincidir con el de {llaves}
    return {"libro_id": libro_id}
```

**Parámetro de consulta (*query parameter*):** va tras el `?`. Para **filtrar,
ordenar, paginar**... Cualquier parámetro de la función que **no** esté en la ruta es de consulta.

```python
@app.get("/libros")
def listar_libros(autor: str, limite: int = 10):    # con valor por defecto → opcional
    return {"autor": autor, "limite": limite}
# GET /libros?autor=Borges&limite=5
# GET /libros?autor=Borges              → limite = 10
# GET /libros                           → 422: falta "autor" (obligatorio)
```

**Los *type hints* (`: int`, `: str`) no son decoración:** FastAPI los usa para
1. **Convertir**: en la URL todo es texto; `"5"` → `5`.
2. **Validar**: `GET /libros/abc` con `libro_id: int` → **422** automático, con un
   JSON que explica qué campo está mal y por qué. Tu función **ni se ejecuta**.
3. **Documentar** (ver 6.5).

**Comprobado en el curso** con un `print()` dentro de la función: con
`/sumar?a=cinco` **no se imprime nada**. El orden es:

```
petición → FastAPI valida los parámetros → ¿válidos? ── no ──▶ 422 (tu función NUNCA se llama)
                                                └─ sí ──▶ llama a tu función con a y b ya convertidos a int
```

Consecuencia: **dentro** de la función puedes fiarte de los tipos. `a` es un
`int`, garantizado; no hace falta comprobar `if isinstance(a, int)`. Cuando
usemos esos valores en SQL, sabremos que `usuario_id` es un número y no texto
cualquiera mandado por un atacante.

> 💡 Ruta vs consulta: `/usuarios/4` → "el usuario 4" (si no existe → 404).
> `/usuarios?activo=true` → "la lista filtrada" (si no hay ninguno → `[]` con 200, no 404).

**Con tipos vs sin tipos** (probado de verdad, con `def sumar(a: int, b: int = 0)` frente a `def sumar(a, b=0)`):

| Petición | Con `: int` | Sin tipos |
|---|---|---|
| `/sumar?a=5&b=3` | `200` `{"resultado": 8}` | `200` `{"resultado": "53"}` 😱 (`"5" + "3"`) |
| `/sumar?a=5` | `200` `{"resultado": 5}` | **`500`** (`"5" + 0` → `TypeError`) |
| `/sumar?a=cinco` | `422` (no es un entero) | **`500`** (`"cinco" + 0`) |
| `/sumar` | `422` (falta `a`) | `422` (falta `a`) |

- Los *type hints* **no son obligatorios** en FastAPI: sin ellos **funciona**,
  pero todo lo que viene de la URL llega como `str`.
- Lo que hace obligatorio un parámetro es **no tener valor por defecto**, no el tipo.
  Por eso `/sumar` da 422 en los dos casos.
- Sin tipos, los errores no desaparecen: pasan de ser un **422 claro** a un
  **500** o, peor aún, a un **200 con un resultado incorrecto**.

**El JSON de un 422** (lo que recibe el frontend):

```json
{"detail": [{"type": "missing", "loc": ["query", "a"], "msg": "Field required", "input": null}]}
```

- `loc` → **dónde** está el problema: en la *query*, en el parámetro `a`.
- `type` / `msg` → **qué** pasa: falta (`missing`) o tipo incorrecto (`int_parsing`).
- `input` → qué valor llegó.
- `detail` es una **lista**: si hay varios campos mal, vienen todos a la vez.

### 6.5 Documentación automática: `/docs`

Con el servidor arrancado, abre **`http://localhost:8000/docs`**:

- **Swagger UI**: una página generada sola, con todos tus endpoints, sus
  parámetros y tipos, y un botón **"Try it out"** para probarlos sin `curl`.
- `http://localhost:8000/redoc` → la misma información con otro diseño.
- `http://localhost:8000/openapi.json` → la especificación **OpenAPI** en bruto
  (lo que usan las dos páginas; también se puede pasar a frontend para generar clientes).

> 💡 En el trabajo, `/docs` es lo primero que se comparte con el equipo de
> frontend: "ahí tenéis todos los endpoints y podéis probarlos".

---

## Lección 7 — Conectar FastAPI con PostgreSQL

### 7.0 El mapa: qué piezas hay y cómo encajan

Antes de entrar en el detalle, la foto completa. Hay **dos momentos** distintos:

**A) Al arrancar la app** (una sola vez):

```
fastapi dev main.py
  └─▶ Python importa main.py
        └─▶ main.py importa db.py
              └─▶ db.py importa config.py
                    └─▶ Settings() lee el .env  → settings.database_url
              └─▶ se crea el pool (todavía cerrado)
        └─▶ se crea app = FastAPI(lifespan=lifespan)
  └─▶ el servidor ejecuta la parte de lifespan ANTES del yield → pool.open()
        └─▶ el pool abre 1 conexión con Postgres (min_size=1)
  └─▶ "Application startup complete" → ya acepta peticiones
```

**B) En cada petición** (`GET /usuarios/1`):

```
llega la petición
  └─▶ FastAPI busca qué función atiende GET /usuarios/{usuario_id}
  └─▶ valida usuario_id: ¿es un int? (si no → 422 y se acaba aquí)
  └─▶ ve que la función necesita "conn: Conn" → ejecuta get_conn() hasta su yield
        └─▶ get_conn pide prestada una conexión al pool
  └─▶ llama a tu endpoint con usuario_id=1 y conn=<la conexión>
        └─▶ tu código: cursor → SQL → fetchone → return dict (o raise 404)
  └─▶ FastAPI convierte lo devuelto a JSON y prepara la respuesta
  └─▶ termina get_conn (lo que hay después del yield)
        └─▶ COMMIT (o ROLLBACK si hubo excepción) y devuelve la conexión al pool
  └─▶ responde al cliente
```

Al apagar (Ctrl+C) se ejecuta la parte de `lifespan` **después** del `yield` → `pool.close()`.

Para entender cada pieza hacen falta unos cuantos conceptos de Python. Vamos por partes.

---

### 7.1 Conceptos de Python que necesitas

#### a) Importar tus propios ficheros (módulos)

Cada fichero `.py` es un **módulo**. Desde un fichero puedes usar lo que hay en otro:

```python
from config import settings     # "del fichero config.py, tráeme la variable settings"
```

- Python busca `config.py` en la carpeta desde la que arrancas (y en las del `.venv`).
- La **primera vez** que se importa un módulo, Python **ejecuta el fichero entero**
  de arriba abajo y guarda el resultado. Las siguientes veces, reutiliza lo guardado.
- Consecuencia: `settings = Settings()` se ejecuta **una sola vez**, y todos los ficheros
  que hacen `from config import settings` comparten **el mismo** objeto. Igual con `pool`.

¿Por qué separar en 3 ficheros? Cada uno tiene **una responsabilidad**:
`config.py` = configuración, `db.py` = acceso a la base de datos, `main.py` = la API.
Cuando el proyecto crezca, sabrás dónde buscar cada cosa.

#### b) Clases y herencia (lo justo)

```python
class Settings(BaseSettings):
    database_url: str
```

- `class Settings` define un **tipo nuevo** de objeto.
- `(BaseSettings)` = **hereda** de `BaseSettings`: Settings recibe "gratis" todo el
  comportamiento que programaron los de pydantic (leer variables de entorno, el `.env`,
  validar tipos...). Tú solo declaras **qué campos** quieres.
- `database_url: str` = "quiero un campo llamado `database_url` y tiene que ser texto".
  Es la misma idea que los *type hints* de los parámetros de FastAPI (lección 6).
- `Settings()` (con paréntesis) = **crear un objeto** de esa clase. Es en ese momento
  cuando se leen y validan las variables.

#### c) Decoradores (repaso)

Un decorador es una función que **recibe otra función y la modifica o la registra**.
La `@` es solo un atajo de escritura:

```python
@app.get("/")
def raiz(): ...

# es exactamente lo mismo que:
def raiz(): ...
raiz = app.get("/")(raiz)     # app.get("/") devuelve un decorador; se le pasa raiz
```

Con `@app.get` el decorador **registra** la función como endpoint. Con
`@asynccontextmanager` (más abajo) el decorador **transforma** la función en otra cosa.

#### d) Gestores de contexto: `with`

Hay recursos que **hay que cerrar siempre**: ficheros, conexiones, cursores...
Si se te olvida, o salta un error antes de cerrar, se quedan abiertos (en
Postgres: conexiones ocupadas para siempre).

```python
# Sin with: si f.read() lanza un error, f.close() nunca se ejecuta
f = open("datos.txt")
contenido = f.read()
f.close()

# Con with: el fichero se cierra SIEMPRE al salir del bloque, haya error o no
with open("datos.txt") as f:
    contenido = f.read()
# aquí f ya está cerrado
```

Un objeto que se puede usar con `with` se llama **gestor de contexto** (*context manager*).
Por dentro tiene dos métodos especiales:

```
with algo as x:          → se llama a algo.__enter__()   y lo que devuelve se guarda en x
    ...bloque...
                         → al salir se llama a algo.__exit__(...)
                           (también si el bloque lanzó una excepción: __exit__ se entera de cuál)
```

Ya los has usado en la lección 5:

```python
with psycopg.connect(url) as conn:     # __enter__: conecta      __exit__: COMMIT/ROLLBACK y cierra
    with conn.cursor() as cur:         # __enter__: crea cursor  __exit__: cierra el cursor
        ...
```

> 💡 Regla de oro: **todo lo que se abre, se abre con `with`**.

#### e) Generadores y `yield`

Una función normal hace `return` y **termina**. Una función con `yield` es un
**generador**: entrega un valor y se queda **pausada** en ese punto, esperando a
que alguien le diga "sigue".

```python
def tres_pasos():
    print("antes")
    yield "valor"          # ← se pausa aquí y entrega "valor"
    print("después")       # ← esto solo se ejecuta cuando alguien la reanude

gen = tres_pasos()         # NO ejecuta nada todavía: solo crea el generador
v = next(gen)              # ejecuta hasta el yield → imprime "antes"; v = "valor"
next(gen)                  # reanuda tras el yield → imprime "después" (y termina → StopIteration)
```

La clave: **una sola función con un "antes" y un "después"**, y en medio, una pausa
en la que **otro código** puede hacer cosas.

#### f) `@contextmanager`: un gestor de contexto hecho con `yield`

Escribir una clase con `__enter__` y `__exit__` es pesado. La librería estándar
(`contextlib`) tiene un decorador que convierte un **generador** en un **gestor de contexto**:

```python
from contextlib import contextmanager

@contextmanager
def cronometro():
    inicio = time.time()           # ← "__enter__": se ejecuta al entrar en el with
    yield                          # ← aquí se ejecuta el bloque del with
    print(time.time() - inicio)    # ← "__exit__": se ejecuta al salir del with

with cronometro():
    hacer_algo_lento()             # ← esto es lo que "ocurre durante el yield"
```

```
lo de ANTES del yield   = preparar        (abrir, conectar, empezar)
el yield                = "ahora haz tu trabajo"
lo de DESPUÉS del yield = limpiar          (cerrar, desconectar, terminar)
```

(Si el bloque lanza una excepción, esta "reaparece" en la línea del `yield`.
Para que la limpieza se haga **sí o sí**, se envuelve en `try: yield finally: limpiar()`
o se usa un `with` dentro, como haremos en `get_conn`.)

#### g) `async`, `await` y `@asynccontextmanager`

**El problema:** un servidor web pasa la mayor parte del tiempo **esperando** (a
la red, a la base de datos...). Si mientras espera a uno no puede atender a otro,
va muy lento.

**`async def`** declara una **corrutina**: una función que puede **pausarse
mientras espera** (con `await`) y dejar que, mientras tanto, se ejecute otra cosa.
Quien reparte el turno entre todas es el **bucle de eventos** (*event loop*), que
en nuestro caso lo pone uvicorn.

```python
async def tarea():
    datos = await pedir_algo_por_red()   # "mientras llega, atiende a otros"
    return datos
```

- Una función `async def` **no se puede llamar normal**: hay que hacer `await tarea()`
  desde otra función async, o dejar que la ejecute el event loop.
- `await` solo se puede usar **dentro** de un `async def`.

**`@asynccontextmanager`** es lo mismo que `@contextmanager` (apartado f), pero
para generadores `async def`. Crea un gestor de contexto **asíncrono**, que se usa
con `async with` en vez de `with`.

**¿Y por qué lo necesitamos?** Porque FastAPI, al arrancar, hace por dentro algo así:

```python
async with lifespan(app):     # ← ejecuta lo de antes del yield (arrancar)
    atender_peticiones()      # ← toda la vida del servidor ocurre "durante el yield"
# ← al apagar: ejecuta lo de después del yield
```

FastAPI **exige** que `lifespan` sea un gestor de contexto asíncrono porque todo
su arranque y apagado funciona con el event loop. Por eso la función es
`async def` y lleva `@asynccontextmanager`, aunque dentro no hagamos ningún `await`.

---

### 7.2 `config.py`: la configuración, línea a línea

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str
    debug: bool = False

settings = Settings()
```

| Línea | Qué hace |
|---|---|
| `from pydantic_settings import ...` | Trae la clase base (`BaseSettings`) y la de configuración (`SettingsConfigDict`). |
| `class Settings(BaseSettings):` | Define tu clase de configuración heredando todo el comportamiento de pydantic-settings (7.1 b). |
| `model_config = SettingsConfigDict(env_file=".env")` | **Configura cómo se comporta la clase**: "además de las variables de entorno, lee el fichero `.env`". `model_config` es un nombre especial que pydantic busca; no es un campo. |
| `database_url: str` | Campo **obligatorio** (no tiene `= valor`). Busca una variable `DATABASE_URL` (no distingue mayúsculas). Si no la encuentra → error al arrancar. |
| `debug: bool = False` | Campo **opcional** con valor por defecto. Si en el `.env` pone `DEBUG=true`, lo convierte a `True` (valida el tipo, igual que FastAPI con los parámetros). |
| `settings = Settings()` | **Aquí ocurre todo**: lee el entorno y el `.env`, convierte, valida y crea el objeto. Se usa como `settings.database_url`. |

**De dónde saca cada valor** (de más a menos prioridad):
1. Variables de entorno reales (`export DATABASE_URL=...`).
2. El fichero `.env`.
3. El valor por defecto del campo.

Así, en producción (donde no hay `.env`) se definen variables de entorno y el
código no cambia.

> ⚠️ `env_file=".env"` es relativo a la **carpeta desde la que arrancas** el
> servidor, no a la del fichero `config.py`. Arranca siempre desde la raíz del proyecto.

---

### 7.3 `db.py`: el pool de conexiones

**Por qué un pool.** Abrir una conexión a Postgres **es caro**: conexión TCP +
autenticación (scram-sha-256) + Postgres **crea un proceso nuevo** para
atenderte. Varios milisegundos cada vez. Además, Postgres tiene un **límite** de
conexiones simultáneas (`max_connections`, por defecto **100**). Con muchas
peticiones abriendo y cerrando conexiones: lento, y al pasar del límite →
`FATAL: sorry, too many clients already`.

Un **pool** (piscina) abre unas cuantas conexiones y las **presta**:

```
petición 1 ──▶ pide prestada la conexión A ──▶ SQL ──▶ la devuelve al pool
petición 2 ──▶ pide prestada la conexión B ──▶ SQL ──▶ la devuelve
petición 3 ──▶ todas ocupadas → ESPERA a que se libere una (no abre más de max_size)
```

```python
from psycopg_pool import ConnectionPool
from config import settings

pool = ConnectionPool(settings.database_url, min_size=1, max_size=5, open=False)
```

| Argumento | Qué hace |
|---|---|
| `settings.database_url` | A qué base de datos conectarse (la URL de siempre). |
| `min_size=1` | Cuántas conexiones mantener **siempre abiertas**, aunque no haya peticiones. |
| `max_size=5` | Cuántas conexiones como **máximo**. Si llegan 6 peticiones a la vez, la 6ª espera (por defecto hasta 30 s; si no se libera ninguna → error `PoolTimeout`). |
| `open=False` | **Crea** el pool pero **no conecta todavía**. Si conectara aquí, lo haría en el momento de **importar** `db.py`: si Postgres no está, la app petaría al importar, y además conectaría en sitios donde no queremos (por ejemplo, en los tests). Lo abriremos explícitamente al arrancar la app (7.4). |

> 💡 En el trabajo: `max_size` × número de copias de la API tiene que caber en
> el `max_connections` del servidor, **compartido con el resto de equipos**.
> Pregunta cuántas conexiones os corresponden.

---

### 7.4 `lifespan`: abrir y cerrar el pool con la app

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from db import pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open()
    yield
    pool.close()

app = FastAPI(lifespan=lifespan)
```

| Línea | Qué hace |
|---|---|
| `from contextlib import asynccontextmanager` | Trae el decorador de 7.1 g. `contextlib` es de la biblioteca estándar de Python. |
| `@asynccontextmanager` | Convierte la función generadora en un gestor de contexto asíncrono, que es lo que FastAPI exige. |
| `async def lifespan(app: FastAPI):` | `async` porque FastAPI lo ejecuta con `async with`. Recibe la `app` (no la usamos, pero FastAPI se la pasa). El nombre `lifespan` ("tiempo de vida") es convención. |
| `pool.open()` | **Antes del `yield`** = al arrancar. Abre el pool: conecta las `min_size` conexiones. Si Postgres no responde, la app **no llega a arrancar** (mejor fallar aquí que en la primera petición). |
| `yield` | "Ya está todo listo: atiende peticiones". La app vive **todo el tiempo** que está pausada aquí. |
| `pool.close()` | **Después del `yield`** = al apagar (Ctrl+C). Cierra todas las conexiones limpiamente. |
| `app = FastAPI(lifespan=lifespan)` | Le dices a FastAPI qué gestor de contexto usar para el arranque y el apagado. Sin esto, la función existe pero nadie la llama. |

En los logs de `fastapi dev` se ve cada fase:

```
INFO:     Waiting for application startup.      ← ejecutando lo de antes del yield
INFO:     Application startup complete.         ← ya está en el yield, atendiendo
INFO:     Waiting for application shutdown.     ← Ctrl+C: ejecutando lo de después
INFO:     Application shutdown complete.
```

---

### 7.5 Dependencias: una conexión por petición con `Depends`

**El concepto (inyección de dependencias).** Muchos endpoints necesitan lo mismo
antes de empezar: una conexión, el usuario que ha iniciado sesión, la
configuración... En vez de que cada endpoint lo consiga por su cuenta, **declara
que lo necesita** y FastAPI **se lo da** ("se lo inyecta").

```python
# db.py
from typing import Annotated
from fastapi import Depends
from psycopg import Connection

def get_conn():
    with pool.connection() as conn:
        yield conn

Conn = Annotated[Connection, Depends(get_conn)]
```

| Línea | Qué hace |
|---|---|
| `def get_conn():` | Una función normal (sin decorador). Es la **dependencia**. |
| `with pool.connection() as conn:` | Pide **prestada** una conexión al pool. Si están todas ocupadas, espera. `pool.connection()` es un gestor de contexto: al salir del `with` hace **`COMMIT`** si no hubo error (o **`ROLLBACK`** si lo hubo) y **devuelve** la conexión al pool (no la cierra). |
| `yield conn` | Entrega la conexión a FastAPI y se **pausa**. FastAPI se la pasa a tu endpoint. Cuando el endpoint termina, FastAPI reanuda `get_conn` → se sale del `with` → commit/rollback + devolver. |
| `Conn = Annotated[Connection, Depends(get_conn)]` | Un **alias** de tipo para no repetirlo en cada endpoint (ver abajo). |

Es el mismo patrón "antes / yield / después" de 7.1 f, pero esta vez quien lo
gestiona es FastAPI: `get_conn` **no** lleva `@contextmanager`; FastAPI reconoce
el `yield` y sabe qué hacer.

**`Annotated` y `Depends`:**

```python
Annotated[Connection, Depends(get_conn)]
#         └─ tipo ─┘  └─── metadato ───┘
```

- `Annotated[Tipo, extra]` es una forma estándar de Python de decir "esto es de tipo
  `Connection`, y además le pego esta información extra". Python ignora el extra;
  **FastAPI lo lee**.
- `Depends(get_conn)` es el extra: "para rellenar este parámetro, ejecuta `get_conn`".
- El tipo `Connection` sirve para que el editor te autocomplete (`conn.cursor()`...).

**Cómo se usa en un endpoint:**

```python
@app.get("/libros")
def listar_libros(conn: Conn):     # ← FastAPI ve "Conn" → ejecuta get_conn() y te pasa la conexión
    ...
```

Para FastAPI hay tres tipos de parámetros: los que están en la ruta `{...}`
(ruta), los que tienen `Depends` (dependencias) y el resto (consulta, `?a=...`).

**Ventaja extra:** los endpoints no saben **de dónde** sale la conexión. En los
tests se puede sustituir `get_conn` por otra que use una base de datos de
pruebas, sin tocar ni un endpoint.

---

### 7.6 Ejecutar SQL y recibir diccionarios: cursor + `dict_row`

```python
from psycopg.rows import dict_row

@app.get("/libros")
def listar_libros(conn: Conn):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT id, titulo FROM libros ORDER BY id")
        return cur.fetchall()
```

| Línea | Qué hace |
|---|---|
| `conn.cursor(...)` | Crea un **cursor**: el objeto por el que mandas SQL y recoges filas. Con `with`, se cierra al acabar. |
| `row_factory=dict_row` | "Fábrica de filas": decide **cómo se construye cada fila**. Por defecto, tuplas `(1, 'Ana')`. Con `dict_row`, diccionarios `{"id": 1, "titulo": "Ana"}`. |
| `cur.execute("SELECT ...")` | Manda el SQL a Postgres. |
| `cur.fetchall()` | Recoge **todas** las filas → lista de diccionarios. Si no hay ninguna → `[]`. |
| `return ...` | FastAPI convierte la lista de diccionarios a JSON y responde **200**. |

**Por qué diccionarios:** JSON es "clave: valor". Con tuplas FastAPI devolvería
`[[1, "Ana"]]` (listas sin nombres); con diccionarios, `[{"id": 1, "titulo": "Ana"}]`.
Las claves son los **nombres de las columnas del `SELECT`** (o sus `AS`), por eso
en un JOIN conviene poner alias (lección 4).

(También se puede configurar para todo el pool:
`ConnectionPool(..., kwargs={"row_factory": dict_row})`, y así no ponerlo en cada cursor.)

---

### 7.7 Parámetros en el SQL: `%s`, **nunca** f-strings 🚨

```python
# ❌ NUNCA: meter datos que vienen de fuera en el SQL con f-string, + o .format()
cur.execute(f"SELECT * FROM libros WHERE titulo = '{titulo}'")

# ✅ SIEMPRE: marcador %s y los valores aparte, en una tupla
cur.execute("SELECT id, titulo FROM libros WHERE titulo = %s", (titulo,))
```

**Por qué (SQL injection):** si alguien manda como `titulo` el texto `x' OR '1'='1`,
la f-string construye:

```sql
SELECT * FROM libros WHERE titulo = 'x' OR '1'='1'    -- '1'='1' siempre es cierto → TODOS los libros
```

El texto del usuario ha **dejado de ser un dato y se ha convertido en SQL**. Con
`'; DROP TABLE libros; --` sería peor.

Con `%s`, psycopg manda a Postgres **el SQL por un lado y los valores por otro**.
Postgres sabe que lo que llega en el hueco es **un valor**, nunca código, por raro
que sea su contenido. (Lo veremos a fondo, atacando nuestra propia API, en la lección 10.)

Detalles de `%s`:
- Se usa `%s` para **cualquier** tipo (número, texto, fecha...), no solo strings. **Sin comillas** alrededor.
- Los valores van en una **tupla**, en el mismo orden que los `%s`.
- Con un solo valor: `(libro_id,)` **con coma**. `(libro_id)` sin coma son solo
  paréntesis alrededor de un número, no una tupla → error.
- Solo sirve para **valores**, no para nombres de tablas o columnas.

---

### 7.8 Uno o ninguno: `fetchone()` y el 404

```python
from fastapi import HTTPException

@app.get("/libros/{libro_id}")
def leer_libro(libro_id: int, conn: Conn):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT id, titulo FROM libros WHERE id = %s", (libro_id,))
        libro = cur.fetchone()

    if libro is None:
        raise HTTPException(status_code=404, detail="Libro no encontrado")
    return libro
```

| Línea | Qué hace |
|---|---|
| `libro_id: int` | Parámetro **de ruta** (está en `{libro_id}`), validado como entero. |
| `conn: Conn` | La conexión prestada (7.5). |
| `... WHERE id = %s", (libro_id,)` | Busca por id, pasando el valor de forma segura (7.7). |
| `cur.fetchone()` | Recoge **una** fila: un diccionario, o **`None`** si la consulta no devolvió nada. |
| `if libro is None:` | `is None` es la forma correcta de comprobar `None` en Python (como `IS NULL` en SQL). |
| `raise HTTPException(status_code=404, detail=...)` | **Lanza** una excepción especial que FastAPI captura y convierte en una respuesta `404` con el JSON `{"detail": "Libro no encontrado"}`. |
| `return libro` | Si existe → 200 con el libro en JSON. |

**`raise` vs `return`:** `raise` **corta** la ejecución en ese punto (lo de debajo
no se ejecuta) y sube por todas las funciones que la llamaron hasta que alguien
la captura (aquí, FastAPI). Si hicieras `return HTTPException(...)`, FastAPI
intentaría devolver el objeto excepción como si fuera un dato normal, con un 200.

---

### 7.9 `def` vs `async def` en los endpoints

psycopg, usado como lo usamos, es **síncrono**: cuando haces `cur.execute(...)`,
el hilo se queda **bloqueado** esperando a Postgres. ¿Cómo atiende entonces
FastAPI varias peticiones a la vez?

| Endpoint declarado con | Cómo lo ejecuta FastAPI | Con psycopg síncrono dentro |
|---|---|---|
| `def` | En un **hilo aparte** (de un grupo de hilos). Si se bloquea, solo se bloquea ese hilo; el resto de peticiones siguen en otros. | ✅ Correcto |
| `async def` | **Directamente en el event loop** (7.1 g), que es **uno solo** para toda la app. | ❌ Mientras espera a Postgres, **toda la API se para** |

**Regla:** si dentro usas código que bloquea (psycopg normal, `requests`,
`time.sleep`...), endpoint con `def`. `async def` solo si todo lo de dentro es
asíncrono (con `await`). Para empezar, **`def` siempre**.

(Existe una versión asíncrona de psycopg, `AsyncConnectionPool`, para usar con
`async def` y `await cur.execute(...)`. Más rendimiento, más complejidad. No la necesitamos todavía.)

---

### 7.10 En proyectos reales: ¿SQL a mano, *query builder* u ORM?

Hay **tres formas** de hablar con la base de datos desde Python, de menos a más
abstracción. La misma consulta ("usuarios activos, ordenados por nombre") en cada una:

**1. SQL a mano con el driver** (lo que hacemos en el curso: psycopg, asyncpg...)

```python
cur.execute("SELECT id, nombre FROM usuarios WHERE activo = %s ORDER BY nombre", (True,))
```

**2. *Query builder*: construyes el SQL con funciones de Python** (SQLAlchemy Core, PyPika...)

```python
stmt = select(usuarios.c.id, usuarios.c.nombre).where(usuarios.c.activo == True).order_by(usuarios.c.nombre)
conn.execute(stmt)
```

**3. ORM (*Object-Relational Mapper*): cada tabla es una clase y cada fila un objeto**
(SQLAlchemy ORM, SQLModel, Django ORM...)

```python
class Usuario(Base):                                  # la tabla, definida como clase
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str]
    activo: Mapped[bool]

usuarios = session.scalars(select(Usuario).where(Usuario.activo).order_by(Usuario.nombre)).all()
usuarios[0].nombre                                    # objetos, no diccionarios
```

| | SQL a mano | Query builder | ORM |
|---|---|---|---|
| Qué escribes | SQL tal cual | Python que genera SQL | Clases y objetos |
| Control sobre el SQL | Total | Alto | Medio (genera él el SQL) |
| Consultas complejas (informes, JOINs raros) | ✅ Lo más fácil | ✅ | ⚠️ A veces se pelea con él |
| Consultas que se construyen según filtros opcionales | ⚠️ Concatenar trozos de SQL es delicado | ✅ Su punto fuerte | ✅ |
| Errores de escritura | Los ves al ejecutar | El editor los detecta antes | El editor los detecta antes |
| Curva de aprendizaje | SQL | SQL + la librería | SQL + bastante librería |
| Peligro típico | Olvidar `%s` → SQL injection | — | Problema **N+1**: sin darte cuenta lanza 1 consulta por fila |

**Qué se usa en la práctica (FastAPI + Postgres):**
- **SQLAlchemy** (versión 2.x) es el estándar de facto en Python: tiene las dos
  capas, *Core* (query builder) y *ORM*, y se pueden mezclar. Va casi siempre
  acompañado de **Alembic** para las migraciones (cambios de esquema versionados).
- **SQLModel** es una capa sobre SQLAlchemy hecha por el autor de FastAPI; une
  los modelos de la base de datos y los de Pydantic.
- **SQL a mano** sigue siendo muy común en equipos pequeños, en APIs de
  **solo lectura / informes** y en partes donde importa mucho el rendimiento.
  Muchos proyectos con ORM tienen también consultas en SQL a mano para lo complejo.

> 💡 **Por qué empezamos con SQL a mano:** un ORM **genera SQL por ti**. Si no
> sabes SQL, cuando algo vaya lento o falle no entenderás qué está haciendo. Todo
> lo que has aprendido (JOINs, índices, transacciones, permisos) se aplica igual
> con un ORM; solo cambia **cómo** lo escribes.
>
> **Para el trabajo:** pregunta qué usa el proyecto. Si os dan un Postgres que
> **ya existe** y lo gestiona otro equipo, es habitual no usar migraciones y,
> o bien escribir SQL a mano, o bien definir en SQLAlchemy solo las tablas que
> vais a usar (o que las lea él solo de la base de datos: *reflection*).

### 7.11 Lecciones de la revisión de código

**`(valor)` no es una tupla, `(valor,)` sí.** Error real del curso:

```python
cur.execute("... WHERE id = %s", (usuario_id))    # → TypeError: object of type 'int' has no len()
cur.execute("... WHERE id = %s", usuario_id)      # → el mismo error (salió otra vez en la lección 8)
cur.execute("... WHERE id = %s", (usuario_id,))   # ✅
```

psycopg intenta contar los parámetros con `len()` y recibe un `int` suelto.
**Regla fija:** el segundo argumento de `execute` es **siempre** una tupla
(`%s`) o un diccionario (`%(nombre)s`), **aunque sea un solo valor**. Si ves
`has no len()` en un `execute`, mira ese segundo argumento.

**En SQL se compara con `=`, no con `==`.** `WHERE id == %s` → error de Postgres
(`operator does not exist`). Python y SQL se mezclan en el mismo fichero: ojo
con cuál de los dos estás escribiendo.

**`fetchall()` nunca devuelve `None`.** Si no hay filas devuelve una lista vacía `[]`.
`if filas is None:` no se cumple jamás (código muerto). Para "¿hay filas?": `if not filas:`.

**Lista vacía ≠ no existe:**

| Petición | Situación | Respuesta correcta |
|---|---|---|
| `GET /usuarios/4/pedidos` | El usuario existe, no tiene pedidos | **`200`** con `[]` |
| `GET /usuarios/999/pedidos` | El usuario **no existe** | **`404`** |

Una lista vacía es una respuesta válida: "no hay ninguno". El 404 es para cuando
**el recurso de la ruta** (`/usuarios/999`) no existe. Por eso hay que comprobar
primero que el usuario existe.

**Comprobar que algo existe → no hace falta traerlo entero:**

```sql
SELECT 1 FROM usuarios WHERE id = %s          -- devuelve una fila con un 1, o ninguna
```

**No hagas JOIN si no lo necesitas.** Para "los pedidos del usuario 5", la tabla
`pedidos` ya tiene `usuario_id`: basta con `SELECT ... FROM pedidos WHERE usuario_id = %s`.
El JOIN solo hace falta si quieres **columnas de la otra tabla** (por ejemplo, el
nombre del usuario). Y todo `JOIN` necesita su `ON` (lección 4.5).

**SQL largo en varias líneas: comillas triples.**

```python
# ⚠️ funciona, pero frágil: dos textos seguidos se pegan solos, y si olvidas
#    el espacio del final queda "...pedidos pWHERE" → syntax error
cur.execute("SELECT id FROM pedidos p "
            "WHERE p.usuario_id = %s", (usuario_id,))

# ✅ más claro: un solo texto que ocupa varias líneas
cur.execute("""
    SELECT id, producto, importe
    FROM pedidos
    WHERE usuario_id = %s
    ORDER BY id
""", (usuario_id,))
```

(La `\` al final de línea no hace falta dentro de paréntesis: Python ya sabe que la expresión continúa.)

**Cómo viajan `Decimal` y `datetime` en el JSON** (respuesta real de `/usuarios/1/pedidos`):

```json
{"id": 1, "producto": "Iphone 18 pro max", "importe": 1883.95, "creado_en": "2026-11-12T09:57:44.206571+00:00"}
```

- `Decimal('1883.95')` → número `1883.95`. FastAPI lo convierte a `float` para el
  JSON; para mostrar precios va bien, pero si el frontend **hace cuentas** con
  dinero, a veces se prefiere mandarlo como texto `"1883.95"` (lo controlaremos
  con los modelos de la lección 8).
- `datetime` → **texto** en formato **ISO 8601**: `fecha T hora +zona`. JSON no
  tiene tipo fecha; el frontend lo vuelve a convertir (en JavaScript: `new Date("2026-11-12T09:57:44+00:00")`).
  El `+00:00` es la zona (UTC): por eso usamos `timestamptz`.

### 7.12 Resumen: qué fichero hace qué

| Fichero | Responsabilidad | Se ejecuta... |
|---|---|---|
| `config.py` | Leer y validar la configuración (`.env`) | Una vez, al importarlo |
| `db.py` | Crear el pool y prestar conexiones (`get_conn`, `Conn`) | El pool: una vez. `get_conn`: en cada petición |
| `main.py` | La app, su `lifespan` y los endpoints | `lifespan`: al arrancar y al apagar. Endpoints: en cada petición |


---

## Lección 8 — CRUD completo con Pydantic

### 8.0 El mapa

Hasta ahora la API solo **leía**. Para **crear y modificar**, el cliente tiene
que **mandarnos datos**, y aparecen dos problemas nuevos:

1. **Lo que entra**: ¿y si el cliente manda un email que no es un email, un
   nombre vacío, un importe negativo, o campos que no existen?
2. **Lo que sale**: ¿cómo garantizamos que la respuesta tiene siempre la misma
   forma y que **nunca** se escapa un campo que no debe salir (una contraseña, un dato interno)?

La herramienta para las dos cosas es **Pydantic**: describes la **forma** de los
datos con una clase, y Pydantic valida, convierte y filtra.

```
POST /usuarios   body: {"nombre": "Eva", "email": "eva@mail.com"}
  └─▶ FastAPI lee el body (JSON) y lo valida contra el modelo de ENTRADA (UsuarioCrear)
        ¿no cuadra? → 422 con el detalle (tu función ni se ejecuta)
  └─▶ llama a tu endpoint con un objeto UsuarioCrear ya validado
        └─▶ INSERT ... RETURNING ...  → dict con la fila creada
  └─▶ FastAPI pasa ese dict por el modelo de SALIDA (UsuarioLeer):
        se queda solo con sus campos, comprueba tipos, convierte a JSON
  └─▶ get_conn: COMMIT y devuelve la conexión
  └─▶ responde 201 Created + el usuario creado
```

---

### 8.1 Mandar datos: el *body* de la petición

En un `GET` los datos van en la URL (ruta y `?consulta`). Para **crear o
modificar**, los datos van en el **cuerpo** (*body*) de la petición, en JSON:

```
POST /libros HTTP/1.1
Content-Type: application/json          ← cabecera: "lo que te mando es JSON"

{"titulo": "Ficciones", "paginas": 200}  ← el body
```

**Por qué no en la URL:** las URLs tienen límite de tamaño, se guardan en logs e
historiales del navegador (mala idea para datos personales) y solo admiten texto
plano. El body admite JSON con estructura (listas, objetos dentro de objetos...).

**Con `curl`:**

```bash
curl -i -X POST "http://localhost:8000/libros" \
     -H "Content-Type: application/json" \
     -d '{"titulo": "Ficciones", "paginas": 200}'
```

| Opción | Qué hace |
|---|---|
| `-X POST` | Usa el método POST (por defecto `curl` hace GET) |
| `-H "Content-Type: application/json"` | Añade la cabecera que dice "el body es JSON" |
| `-d '...'` | El body. Entre comillas **simples** por fuera, para poder usar comillas **dobles** dentro (el JSON las exige) |

(En `/docs` es más cómodo: "Try it out" te deja editar el body en un cuadro.)

#### ¿Por qué `application/json`? Los tipos MIME

El body es **solo una ristra de bytes**. `{"titulo": "Ficciones"}` podría ser
JSON, texto plano o un trozo de formulario. El servidor no lo adivina, así que
el cliente lo **declara** en la cabecera `Content-Type` con un **tipo MIME**
(*media type*). Tiene el formato `tipo/subtipo`:

| Tipo MIME | Qué es | Dónde lo verás |
|---|---|---|
| `application/json` | JSON | APIs como la nuestra |
| `application/x-www-form-urlencoded` | `titulo=Ficciones&paginas=200` | formularios HTML clásicos |
| `multipart/form-data` | campos + ficheros | subir ficheros |
| `text/plain` | texto sin formato | — |
| `text/html` | una página web | navegador |
| `image/png` | una imagen | — |

**¿Por qué "application" y no "text"?** La primera parte es la familia:
`text/` es texto para leerlo una persona, `image/` imágenes, y `application/`
son datos **para que los procese un programa**. JSON es eso: datos
estructurados que va a parsear una aplicación, así que el nombre oficial
(RFC 8259) es `application/json`.

**La trampa de `curl`:** si usas `-d` **sin** `-H`, `curl` manda por defecto
`Content-Type: application/x-www-form-urlencoded`. FastAPI no lo lee como JSON
y devuelve un 422 (comprobado):

```json
{"detail": [{"type": "model_attributes_type", "loc": ["body"],
  "msg": "Input should be a valid dictionary or object to extract fields from",
  "input": "{\"titulo\": \"Ficciones\"}"}]}
```

Fíjate en el `input`: le ha llegado el texto **como un string**, no como un
objeto. Si ves este error, lo primero es comprobar la cabecera.

**Y al revés:** en la respuesta, el servidor también manda `Content-Type`. Con
`curl -i` verás `content-type: application/json`, y así el cliente sabe cómo
leer lo que le devuelven. Lo ves en cada respuesta, y FastAPI la pone solo.

---

### 8.2 Pydantic: describir la forma de los datos

#### a) `BaseModel`: un modelo es una clase con campos tipados

Ya lo viste con `Settings` (lección 7): heredar de una clase de Pydantic y
declarar campos con tipo. `BaseModel` es la clase base general:

```python
from pydantic import BaseModel

class LibroCrear(BaseModel):
    titulo: str
    paginas: int

libro = LibroCrear(titulo="Ficciones", paginas="200")   # "200" → 200 (convierte)
libro.titulo        # "Ficciones"   ← se accede con punto, como atributos
libro.paginas       # 200 (int)

LibroCrear(titulo="Ficciones", paginas="muchas")
# ValidationError: paginas → Input should be a valid integer
```

Al crear el objeto, Pydantic **valida y convierte** cada campo. Si algo no
cuadra, lanza `ValidationError` con el detalle de **todos** los campos mal.
FastAPI captura ese error y lo convierte en el **422** que ya conoces.

#### b) Campos opcionales y valores por defecto

```python
class LibroCrear(BaseModel):
    titulo: str                        # obligatorio
    subtitulo: str | None = None       # opcional: puede no venir, o venir null
    disponible: bool = True            # opcional: si no viene, True
```

- `str | None` se lee "texto **o** None". El `|` entre tipos significa "o".
- `= None` / `= True` → el valor por defecto. **Tener valor por defecto es lo que
  hace opcional a un campo** (igual que con los parámetros de las funciones).
- `str | None` sin `= None` → obligatorio, pero puede valer `null`. Raro; casi siempre van juntos.

#### c) Restricciones con `Field`

El tipo dice "es un texto"; `Field` añade **reglas** ("de 1 a 100 caracteres"):

```python
from decimal import Decimal
from pydantic import BaseModel, Field

class LibroCrear(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    paginas: int = Field(gt=0)                      # gt = greater than: > 0
    precio: Decimal = Field(ge=0, max_digits=10, decimal_places=2)   # ge: >= 0; como numeric(10,2)
```

| Restricción | Para | Significa |
|---|---|---|
| `min_length` / `max_length` | textos, listas | longitud mínima / máxima |
| `gt` / `ge` | números | mayor que / mayor o igual que |
| `lt` / `le` | números | menor que / menor o igual que |
| `max_digits` / `decimal_places` | `Decimal` | dígitos totales / decimales (como `numeric(10,2)`) |
| `pattern` | textos | tiene que cumplir una expresión regular |

- `Field(...)` va **en el lugar del valor por defecto**. Si además quieres un
  valor por defecto: `Field(default=10, gt=0)`.
- **¿Duplicar las reglas que ya tiene Postgres (`CHECK`, `NOT NULL`)?** Sí, y es
  bueno: Postgres es la **última defensa** (lección 3); Pydantic da al cliente un
  **422 con un mensaje claro** antes de llegar a la base de datos, en vez de un
  error de Postgres que hay que traducir.

#### d) Tipos especiales: `EmailStr`

```python
from pydantic import EmailStr

class AutorCrear(BaseModel):
    email: EmailStr          # valida que tenga forma de email (necesita email-validator, que viene con fastapi[standard])
```

#### e) Convertir un modelo a diccionario: `model_dump()`

```python
libro = LibroCrear(titulo="Ficciones", paginas=200)
libro.model_dump()                     # {"titulo": "Ficciones", "subtitulo": None, "disponible": True, ...}
libro.model_dump(exclude_unset=True)   # {"titulo": "Ficciones", "paginas": 200}  ← solo lo que se MANDÓ
```

`exclude_unset=True` deja fuera los campos que el cliente **no mandó** (aunque
tengan valor por defecto). Será clave para el PATCH.

> ⚠️ **Con paréntesis: `model_dump()`.** Sin ellos, `libro.model_dump` no
> **llama** al método, solo lo **nombra** (es la función en sí, no su
> resultado). Error real del curso (comprobado):
>
> ```python
> {**pedido.model_dump, "usuario_id": 5}     # ❌ TypeError: 'method' object is not a mapping
> {**pedido.model_dump(), "usuario_id": 5}   # ✅ primero se llama → dict → se desparrama
> ```
>
> `'method' object is not a mapping` = "me has dado un método y yo esperaba un
> diccionario". Si en un error ves `'method'` o `'function'` donde esperabas un
> valor, casi siempre faltan unos `()`.

---

### 8.3 Varios modelos para un mismo recurso

Lo normal es **no** usar un solo modelo para todo, sino uno por "dirección":

| Modelo | Para | Qué campos |
|---|---|---|
| `LibroCrear` | **Entrada** del `POST` | Lo que el cliente **puede y debe** mandar. Sin `id` ni `creado_en`: los pone Postgres |
| `LibroActualizar` | **Entrada** del `PATCH` | Los mismos, pero **todos opcionales** (se cambia solo lo que venga) |
| `LibroLeer` | **Salida** de todos | Lo que el cliente **puede ver**: incluye `id` y `creado_en` |

¿Por qué separarlos? Si el `POST` aceptara `id`, el cliente podría elegir el id
(¡o intentar pisar otro!). Si la salida fuera "lo que haya en la tabla", el día
que añadas una columna `password_hash` saldría en la API. **Cada modelo es un
contrato**: esto es exactamente lo que entra y lo que sale.

#### ¿Y `Mapped`? Dos tipos de "modelo" que se parecen mucho

En proyectos con SQLAlchemy verás clases muy parecidas a estas, pero con
`Mapped[...]`. **No son lo mismo**: la palabra "modelo" se usa para dos cosas.

```python
# models.py: modelo ORM (SQLAlchemy). Describe la TABLA de la base de datos
class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]

# schemas.py: modelo Pydantic. Describe el JSON que ENTRA o SALE de la API
class UsuarioLeer(BaseModel):
    id: int
    email: str            # sin password_hash: no sale nunca en la API
```

| | Modelo ORM (`Mapped`) | Modelo Pydantic (`BaseModel`) |
|---|---|---|
| Librería | SQLAlchemy | Pydantic |
| Describe | Una **tabla** (columnas, PK, FK...) | Un **JSON** de la API (entrada o salida) |
| Sirve para | Leer y escribir filas **sin escribir SQL** | Validar lo que entra y filtrar lo que sale |
| Cuántos por recurso | Normalmente **uno** (una tabla) | **Varios** (`Crear`, `Actualizar`, `Leer`...) |
| Fichero habitual | `models.py` | `schemas.py` |

**`Mapped[int]`** es una anotación de tipo de SQLAlchemy 2.x. Le dice: "este
atributo es una columna, y en Python vale un `int`". Así el editor sabe que
`usuario.id` es un `int`. `mapped_column(...)` añade los detalles de la
columna (clave primaria, `unique`, `nullable`...).

**Por qué no lo usamos aún:** nosotros hablamos con Postgres con **SQL a mano**
(psycopg), así que la tabla ya está descrita en el `CREATE TABLE` y no
necesitamos una clase ORM. Solo tenemos la capa de Pydantic. `Mapped` llega en
la **lección 12**. Allí verás que en un proyecto con ORM conviven las dos capas:
el endpoint lee un `Usuario` (ORM) de la base de datos y lo devuelve como
`UsuarioLeer` (Pydantic) gracias a `model_config = ConfigDict(from_attributes=True)`.

> ⚠️ **No uses el modelo ORM como respuesta de la API.** Sería volver al problema
> de antes: la tabla tiene columnas (`password_hash`) que el cliente no debe ver.
> (SQLModel intenta unir las dos capas en una sola clase; ya lo verás.)

---

### 8.4 Modelo de entrada: FastAPI lo lee del body

```python
@app.post("/libros")
def crear_libro(libro: LibroCrear, conn: Conn):
    ...
```

Ya sabíamos cómo decide FastAPI de dónde sale cada parámetro. Se añade una regla:

| El parámetro... | Sale de |
|---|---|
| está en la ruta `{...}` | la ruta |
| tiene `Depends` | una dependencia |
| es un **modelo de Pydantic** (`BaseModel`) | el **body** (JSON) ← nuevo |
| cualquier otro (`int`, `str`...) | la consulta `?...` |

Dentro de la función, `libro` ya es un objeto `LibroCrear` **validado**:
`libro.titulo` es un `str` de 1 a 200 caracteres, garantizado.

**El 422 de un body** dice exactamente qué campo falla:

```json
{"detail": [{"type": "greater_than", "loc": ["body", "paginas"], "msg": "Input should be greater than 0", "input": -5}]}
```

(`"loc": ["body", "paginas"]` → en el body, campo `paginas`.)

---

### 8.5 Modelo de salida: `response_model`

```python
@app.get("/libros/{libro_id}", response_model=LibroLeer)
def leer_libro(libro_id: int, conn: Conn):
    ...
    return libro          # un dict
```

`response_model=LibroLeer` le dice a FastAPI: "lo que devuelva esta función,
**pásalo por `LibroLeer` antes de responder**". Eso hace tres cosas:

1. **Filtra**: solo salen los campos del modelo. Si el `dict` trae columnas de
   más, **se descartan**. Si un día haces `SELECT *` sin querer, no se escapa nada.
2. **Valida**: si falta un campo o tiene el tipo equivocado → error **500**. Es un
   bug **tuyo** (tu código no cumple su propio contrato) y prefieres enterarte.
3. **Documenta**: `/docs` muestra la forma exacta de la respuesta.

#### #### El **filtro** manda: si un campo no está en el `response_model`, no sale

El paso 1 (filtrar) funciona **siempre**, aunque tu función devuelva más datos.
Error típico (le pasó a Rubén en el ejercicio 4) → poner el modelo de **entrada**
como modelo de **salida**:

```python
@app.post("/usuarios", response_model=UsuarioCrear, status_code=201)   # ❌ modelo de ENTRADA
def crear_usuario(usuario: UsuarioCrear, conn: Conn):
    ...
    # el INSERT ... RETURNING devuelve:  {"id": 8, "nombre": "Juan", "email": "...", "creado_en": ...}
    # UsuarioCrear solo tiene nombre y email → FastAPI tira lo demás
    # el cliente recibe:                 {"nombre": "Juan", "email": "juan@mail.com"}
```

No da error: el `dict` **tiene** `nombre` y `email`, así que cumple el
contrato de `UsuarioCrear`. Los campos de más se descartan en silencio. Por eso
cuesta verlo: parece que Postgres no ha devuelto el `id`, pero sí lo ha
devuelto, y se ha perdido en el filtro.

**Regla:** en el decorador va el modelo de **salida** (`...Leer`); en el
parámetro de la función, el de **entrada** (`...Crear` / `...Actualizar`).

```python
@app.post("/usuarios", response_model=UsuarioLeer, status_code=201)   # sale: UsuarioLeer
def crear_usuario(usuario: UsuarioCrear, conn: Conn):                 # entra: UsuarioCrear
```

Y el `RETURNING` tiene que traer **todos** los campos de `UsuarioLeer`. Si falta
uno (por ejemplo `activo`), ya no es un filtro, sino un contrato roto → **500**.

| Lo que devuelve tu función respecto al `response_model` | Resultado |
|---|---|
| Tiene campos **de más** | Se quitan en silencio → 200/201 |
| Le **falta** un campo obligatorio | `ResponseValidationError` → **500** |

**Cómo se ve en la terminal** (comprobado: `UsuarioLeer` con `activo` y un
`RETURNING id, nombre, email, creado_en` sin `activo`):

```
fastapi.exceptions.ResponseValidationError: 1 validation error:
  {'type': 'missing', 'loc': ('response', 'activo'), 'msg': 'Field required',
   'input': {'id': 11, 'nombre': 'Prueba', 'email': '...', 'creado_en': ...}}
```

| Trozo | Qué te dice |
|---|---|
| `ResponseValidationError` | Ha fallado la **respuesta** (tu código), no lo que mandó el cliente |
| `'loc': ('response', 'activo')` | En la respuesta, el campo `activo`. Compáralo con el 422, donde `loc` empieza por `'body'` |
| `'type': 'missing'` | No está |
| `'input': {...}` | Lo que devolvió tu función: aquí ves que le falta `activo` |

Es el "espejo" del 422: el **422** es "cliente, lo que me mandas no cumple el
contrato"; este **500** es "programador, lo que devuelves no cumple el contrato".

**¿Se guardó la fila?** No (comprobado). Con `scope="function"` (8.9), la
respuesta se valida **antes** de que `get_conn` haga el `COMMIT`. La excepción
llega hasta el `with pool.connection()` → **`ROLLBACK`**. Justo lo que queremos:
si la API responde error, no se ha guardado nada a medias.

> 💡 **Pero el `id` sí se gasta.** En la prueba, el `INSERT` deshecho se llevó el
> `id` 11, y el siguiente usuario será el 12, no el 11. Las secuencias de
> `IDENTITY` **no** vuelven atrás con el `ROLLBACK` (así dos transacciones a la vez
> nunca reciben el mismo número). Los huecos en los ids son normales: **nunca**
> cuentes con que los ids sean consecutivos.

#### Para devolver **varios**: `list[...]`

Un modelo describe **un** objeto. Si el endpoint devuelve muchos (un listado),
el JSON es una **lista** de esos objetos, y así se declara:

```python
@app.get("/libros", response_model=list[LibroLeer])
def listar_libros(conn: Conn):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT id, titulo, paginas, precio, creado_en FROM libros ORDER BY id")
        return cur.fetchall()          # lista de dicts
```

| Endpoint | Devuelve | `fetch...` | `response_model` |
|---|---|---|---|
| `GET /libros` | **una lista** de libros | `fetchall()` → `list[dict]` | `list[LibroLeer]` |
| `GET /libros/{id}` | **un** libro | `fetchone()` → `dict` | `LibroLeer` |

- `list[LibroLeer]` se lee "lista de `LibroLeer`". Es la misma sintaxis de tipos
  que `list[int]` o `str | None`: los corchetes dicen **de qué** es la lista.
- FastAPI pasa **cada elemento** por `LibroLeer` (filtra, valida y convierte uno a uno).
- Una tabla vacía devuelve `[]`, y eso es válido: una lista vacía sigue siendo una
  lista de `LibroLeer`. **No** es un 404: "no hay libros" es una respuesta correcta.
- **No hace falta un modelo nuevo** tipo `LibrosLeer`: el modelo describe una fila
  y `list[...]` dice que vienen varias.
- Si te equivocas y pones `response_model=LibroLeer` con `fetchall()`, FastAPI
  intenta meter una lista donde espera un objeto → **500** (`ResponseValidationError`).

**Cambio de formato que vas a notar:** con un modelo de Pydantic de por medio,
`Decimal` sale en el JSON como **texto**: `"precio": "1883.95"` (antes salía
`1883.95` como número). Pydantic lo hace a propósito para **no perder precisión**:
un número JSON se suele leer como `float`, y con dinero no queremos `float`.

---

### 8.6 POST: crear (`INSERT ... RETURNING`)

```python
@app.post("/libros", response_model=LibroLeer, status_code=201)
def crear_libro(libro: LibroCrear, conn: Conn):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            INSERT INTO libros (titulo, paginas, precio)
            VALUES (%(titulo)s, %(paginas)s, %(precio)s)
            RETURNING id, titulo, paginas, precio, creado_en
        """, libro.model_dump())
        return cur.fetchone()
```

| Línea | Qué hace |
|---|---|
| `@app.post(...)` | Responde a `POST /libros`. |
| `status_code=201` | Si todo va bien, responde **201 Created** en vez de 200 (lección 6.1). |
| `libro: LibroCrear` | El body, ya validado (8.4). |
| `%(titulo)s` | **Marcador con nombre**: igual que `%s`, pero el valor se busca en un **diccionario** por su nombre. Seguro igual que `%s` (7.7). Con muchas columnas es mucho más legible que contar `%s`. |
| `libro.model_dump()` | Convierte el modelo en `{"titulo": ..., "paginas": ..., "precio": ...}`: el diccionario de donde salen los `%(nombre)s`. |
| `RETURNING id, ...` | Lección 3.8: el `INSERT` devuelve la fila creada, **con el `id` y el `creado_en` que ha generado Postgres**. Sin esto tendrías que hacer otro `SELECT` (y saber qué id le tocó). |
| `return cur.fetchone()` | La fila creada (dict) → pasa por `LibroLeer` → JSON. **Va dentro del `with`** (ver abajo). |

> ⚠️ **`fetchone()` / `fetchall()` siempre DENTRO del `with conn.cursor()`.**
> Al salir del bloque `with`, el cursor **se cierra**, y con él los resultados
> que tenía guardados. Si lees después, falla (comprobado en el curso):
>
> ```python
> with conn.cursor(row_factory=dict_row) as cur:
>     cur.execute("INSERT ... RETURNING ...", datos)
> return cur.fetchone()      # ❌ fuera del with → cursor cerrado
> # psycopg.InterfaceError: the cursor is closed   → 500
> ```
>
> El cliente solo ve `500 Internal Server Error`. **La causa real está siempre en
> la terminal de `fastapi dev`**: busca la última línea del traceback (el error) y
> la línea de **tu** fichero (`File ".../main.py", line 64`).
>
> Dos formas correctas: hacer `return` dentro del `with`, o guardar el
> resultado en una variable dentro y usarla fuera (como en el PATCH de 8.7):
>
> ```python
> with conn.cursor(row_factory=dict_row) as cur:
>     cur.execute(...)
>     usuario = cur.fetchone()   # ✅ se lee con el cursor abierto
> return usuario                 # ✅ la variable es un dict normal, ya no depende del cursor
> ```
>
> **¿Se guardó la fila?** No. La excepción sube hasta `get_conn`; el
> `with pool.connection()` ve un error y hace **`ROLLBACK`** en vez de `COMMIT`. El
> `INSERT` se deshace, así que puedes repetir la petición con el mismo email.

**Marcadores con nombre vs posicionales** (no se pueden mezclar en la misma consulta):

```python
cur.execute("... WHERE id = %s AND activo = %s", (5, True))                         # posición → tupla
cur.execute("... WHERE id = %(id)s AND activo = %(activo)s", {"id": 5, "activo": True})  # nombre → dict
```

**Anatomía de un marcador con nombre:** `%(activo)s` tiene **tres** partes, y
la `s` del final **es obligatoria**:

```
%(activo)s
│└──┬───┘└─ formato: s = "lo que sea, psycopg se encarga del tipo" (usa siempre s)
│   └────── nombre: la clave del diccionario
└────────── empieza un marcador
```

Error típico (le pasó a Rubén en el PATCH): olvidar la `s` → `%(activo)`.
psycopg lo detecta **antes** de mandar nada a Postgres (comprobado):

```
psycopg.ProgrammingError: only '%s', '%b', '%t' are allowed as placeholders, got '%(activo),'
```

Se lee: "después de `%(activo)` esperaba `s` (o `b`/`t`, formatos binario/texto
que no vas a necesitar), y lo que he encontrado es una `,`". El `got '...'` te
enseña **el trozo exacto** del SQL donde está el fallo: búscalo en tu consulta.
Como pasa antes de tocar la base de datos, no se cambia nada → **500** sin efectos.

---

### 8.7 PATCH: modificar solo lo que venga

**`PUT` vs `PATCH`:**
- `PUT /libros/5` → "**reemplaza** el libro 5 por este" → hay que mandar **todos** los campos.
- `PATCH /libros/5` → "**cambia** estos campos del libro 5" → se manda **solo lo que cambia**.

En la práctica `PATCH` es lo más usado para editar. El modelo de entrada tiene **todos los campos opcionales**:

```python
class LibroActualizar(BaseModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    paginas: int | None = Field(default=None, gt=0)
    precio: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
```

**El SQL: `COALESCE` para "si no viene, deja lo que había"** (lección 4.5):

```python
@app.patch("/libros/{libro_id}", response_model=LibroLeer)
def actualizar_libro(libro_id: int, cambios: LibroActualizar, conn: Conn):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            UPDATE libros SET
                titulo  = COALESCE(%(titulo)s,  titulo),
                paginas = COALESCE(%(paginas)s, paginas),
                precio  = COALESCE(%(precio)s,  precio)
            WHERE id = %(id)s
            RETURNING id, titulo, paginas, precio, creado_en
        """, {**cambios.model_dump(), "id": libro_id})
        libro = cur.fetchone()
    if libro is None:
        raise HTTPException(status_code=404, detail="Libro no encontrado")
    return libro
```

| Pieza | Qué hace |
|---|---|
| `COALESCE(%(titulo)s, titulo)` | Si el cliente mandó `titulo`, usa ese. Si no (`None` → `NULL`), `COALESCE` devuelve el segundo: la columna `titulo`, **su valor actual**. Es decir, no lo cambia. |
| `{**cambios.model_dump(), "id": libro_id}` | `**` "desparrama" un diccionario dentro de otro: el resultado es `{"titulo": ..., "paginas": ..., "precio": ..., "id": 5}`. Así todos los marcadores tienen su valor. |
| `RETURNING ...` + `fetchone()` | Si el id no existe, el `UPDATE` no toca ninguna fila → `RETURNING` no devuelve nada → `None` → 404. Una sola consulta para actualizar **y** saber si existía. |

> ⚠️ **Limitación de `COALESCE`:** con este truco **no se puede poner una
> columna a `NULL`** (un `null` se interpreta como "no lo cambies"). Para columnas
> `NOT NULL` (como todas las nuestras) da igual. Si algún día lo necesitas, hay que
> construir el `SET` solo con los campos de `model_dump(exclude_unset=True)`,
> usando `psycopg.sql` para meter nombres de columnas de forma segura (los nombres
> de columna **no** pueden ir en `%s`). Lo veremos si hace falta.

---

### 8.8 DELETE: borrar y responder `204`

```python
@app.delete("/libros/{libro_id}", status_code=204)
def borrar_libro(libro_id: int, conn: Conn):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM libros WHERE id = %s", (libro_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Libro no encontrado")
```

| Pieza | Qué hace |
|---|---|
| `status_code=204` | **204 No Content**: "hecho, y no tengo nada que devolverte". Una respuesta 204 **no lleva body**. |
| `cur.rowcount` | Cuántas filas tocó la última sentencia: es el número de `DELETE 1` que veías en `psql` (lección 3.8). `0` → no existía → 404. |
| Sin `return` | La función devuelve `None` → FastAPI responde 204 sin cuerpo. |

**¿204 o 200?** Las dos son "ha ido bien" (todo lo que empieza por **2** es éxito). La
diferencia es **si devuelves algo**:

| Opción | Cuándo | Cómo |
|---|---|---|
| **204 No Content** ✅ lo habitual | No devuelves nada: "borrado, no hay más que decir" | `status_code=204`, sin `return` |
| **200 OK** | Devuelves algo, por ejemplo la fila que se acaba de borrar (`DELETE ... RETURNING ...`) | `response_model=LibroLeer`, con `return` |

Si no pones `status_code`, FastAPI responde **200** con body `null`, que funciona
pero es raro: un 200 promete contenido y no hay. Si no devuelves nada, usa **204**.

> ⚠️ **No mezcles las dos opciones.** `response_model=...` + `status_code=204`
> es una contradicción ("devuelve esta forma" + "no devuelvas nada"), y FastAPI se
> niega a **arrancar** (comprobado en el ejercicio 6):
>
> ```
> AssertionError: Status code 204 must not have a response body
> ```
>
> Ojo: no falla al llamar al endpoint, falla al **arrancar la app** (al registrar
> la ruta). Con `fastapi dev`, el servidor se queda caído y **ningún** endpoint
> responde. Si tras guardar un cambio todo deja de contestar, mira la terminal.
>
> Elige una: o `status_code=204` sin `response_model` ni `RETURNING`, o
> `response_model=UsuarioLeer` con 200 y `RETURNING`.

**Chuleta de códigos de éxito del CRUD:**

| Operación | Método | Éxito |
|---|---|---|
| Leer uno / listar | `GET` | **200** + el recurso / la lista |
| Crear | `POST` | **201 Created** + lo creado |
| Modificar | `PATCH` | **200** + cómo ha quedado |
| Borrar | `DELETE` | **204 No Content**, sin body |

> ⚠️ Borrar un libro que tenga filas que lo referencien (una clave foránea, lección 4)
> lanzará `ForeignKeyViolation` → **500**. En la lección 9 lo convertiremos en un **409 Conflict**.

---

### 8.9 Que el `COMMIT` ocurra **antes** de responder: `scope="function"`

Ahora que **escribimos**, importa **cuándo** se hace el `COMMIT`. Recuerda que lo
hace `get_conn` al salir del `with pool.connection()` (7.5), es decir, en la parte
**después del `yield`**.

**Por defecto, FastAPI ejecuta lo de después del `yield` cuando la respuesta ya
se ha enviado al cliente.** Comprobado en el curso con una dependencia cuyo
"después del yield" fallaba a propósito (simulando un `COMMIT` que falla):

```
sin scope:              201 {"ok": true}           ← el cliente cree que se guardó... y no
scope="function":       500 Internal Server Error   ← el cliente se entera del fallo
```

El `COMMIT` puede fallar (se cae la conexión, un conflicto con otra transacción...).
Si ya respondiste "201 Creado", **le has mentido al cliente**. Solución: decirle a
FastAPI que cierre la dependencia **en cuanto termine la función del endpoint,
antes de enviar la respuesta**:

```python
Conn = Annotated[Connection, Depends(get_conn, scope="function")]
```

| `scope` | Lo de después del `yield` se ejecuta... |
|---|---|
| `"request"` (por defecto) | **después** de enviar la respuesta |
| `"function"` | al terminar el endpoint, **antes** de enviar la respuesta |

> 💡 Para dependencias que hacen `COMMIT`, `scope="function"`. La respuesta
> solo debe salir cuando los datos están **de verdad** guardados.

---

### 8.10 Permisos: la API ahora necesita escribir

`api_curso` solo tiene `SELECT` (lección 2). Un `INSERT` desde la API daría
`permission denied for table usuarios` → `psycopg.errors.InsufficientPrivilege` → **500**.

Hay que darle (como `postgres`) **exactamente** lo que vaya a usar, tabla a tabla:
`INSERT` (`a`), `UPDATE` (`w`), `DELETE` (`d`). Mínimo privilegio: si un endpoint
no borra pedidos, el rol no necesita `DELETE` sobre `pedidos`.

Con `GENERATED ... AS IDENTITY` no hace falta permiso sobre la secuencia (lección 3.4).

En nuestro contenedor ya está hecho. `\dp` muestra `api_curso=arwd/postgres` en
`usuarios` y `pedidos`: `a`=INSERT, `r`=SELECT, `w`=UPDATE, `d`=DELETE.

---

### 8.11 ✏️ Ejercicios de la lección 8

Hasta ahora todo era con `libros` de ejemplo. Ahora te toca hacerlo de verdad sobre
**nuestras tablas**, `usuarios` y `pedidos` (lección 4.5). Tú escribes el código y
Claude lo revisa. Pruébalo todo con `curl -i` o en `/docs`.

Recordatorio de las tablas:

```
usuarios: id (identity) · nombre text NOT NULL · email text NOT NULL UNIQUE · activo bool DEFAULT true · creado_en timestamptz DEFAULT now()
pedidos:  id (identity) · usuario_id int NOT NULL → usuarios(id) · producto text NOT NULL · importe numeric(10,2) NOT NULL CHECK >= 0 · creado_en timestamptz DEFAULT now()
```

**Ejercicio 1: `scope="function"` (8.9)**
Cambia `Conn` en `db.py` para que el `COMMIT` ocurra antes de responder.

**Ejercicio 2: `schemas.py` con los modelos Pydantic (8.2 y 8.3)**
Crea un fichero nuevo `schemas.py` con:

| Modelo | Campos |
|---|---|
| `UsuarioCrear` | `nombre` (1–100 caracteres), `email` (`EmailStr`) |
| `UsuarioActualizar` | `nombre`, `email`, `activo`, **todos opcionales** |
| `UsuarioLeer` | `id`, `nombre`, `email`, `activo`, `creado_en` (tipo: `datetime`, de `from datetime import datetime`) |
| `PedidoCrear` | `producto` (1–200 caracteres), `importe` (`Decimal`, `>= 0`, como `numeric(10,2)`) |
| `PedidoLeer` | `id`, `usuario_id`, `producto`, `importe`, `creado_en` |

Pregunta: ¿por qué `UsuarioCrear` no tiene `activo`? ¿Debería tenerlo?

**Ejercicio 3: `response_model` en los GET que ya tienes (8.5)**
Ponle `response_model` a `GET /usuarios`, `GET /usuarios/{id}` y
`GET /usuarios/{id}/pedidos`. Los dos primeros no devuelven `creado_en` y
`UsuarioLeer` sí lo exige: ¿qué pasa si no lo añades al `SELECT`? Pruébalo antes
de arreglarlo y fíjate en qué código HTTP sale y **de quién es la culpa**.

**Ejercicio 4: `POST /usuarios` → 201 (8.6)**
Pruébalo con:
1. Un usuario correcto. Comprueba en la respuesta que vienen `id`, `activo` y `creado_en`.
2. `"email": "esto-no-es-un-email"` → ¿qué código? ¿Qué dice `loc`?
3. `"nombre": ""` → ídem.
4. Un email que **ya existe** (`luis@mail.com`) → ¿qué código sale? Mira la
   terminal de `fastapi dev`: ¿qué excepción de psycopg aparece? (Se arregla en la
   lección 9, de momento solo **obsérvalo**).
5. Manda un campo de más: `{"nombre": "X", "email": "x@mail.com", "id": 999}`.
   ¿Se queja? ¿Qué `id` le pone Postgres?

**Ejercicio 5: `PATCH /usuarios/{id}` (8.7)**
Pruébalo con:
1. `{"activo": false}` → solo cambia `activo`.
2. `{}` → ¿qué devuelve? ¿Ha cambiado algo?
3. Un id que no existe → 404.
4. `{"nombre": ""}` → 422.
5. `{"email": "marta@mail.com"}` sobre **otro** usuario → ¿qué pasa? (Lo mismo que en 4.4.)

**Ejercicio 6: `DELETE /usuarios/{id}` → 204 (8.8)**
1. Crea un usuario con el POST y bórralo → 204, sin body.
2. Bórralo otra vez → 404.
3. Intenta borrar a Luis (tiene pedidos) → ¿qué código? ¿Qué excepción sale en la terminal?

**Ejercicio 7: `POST /usuarios/{usuario_id}/pedidos` → 201**
Crear un pedido **para un usuario**. Es un recurso anidado: el `usuario_id` viene
de la **ruta**, no del body, así que `PedidoCrear` no lo lleva.
1. Un pedido correcto para Luis.
2. `"importe": -5` → ¿quién lo para, Pydantic o Postgres? ¿Cómo lo sabes?
3. `"importe": 10.999` → ¿y esto?
4. Para un usuario que **no existe** (`/usuarios/999/pedidos`) → ¿qué sale?
   Piensa cómo lo convertirías en un 404 con lo que ya sabes (pista: el
   `GET /usuarios/{id}/pedidos` que ya tienes).

**🎯 Bonus: prohibir campos de más**
En el ejercicio 4.5 habrás visto que Pydantic **ignora** los campos que no
conoce. Busca en la documentación de Pydantic `ConfigDict(extra=...)` y haz
que `UsuarioCrear` responda **422** si le mandan un campo que no existe.
¿Por qué podría interesar esto? ¿Y por qué podría molestar?

> 💡 Apunta los códigos y las excepciones que veas en los ejercicios 4.4, 5.5, 6.3
> y 7.4. Son justo lo que arreglaremos en la **lección 9**: pasar de "500 y un
> traceback" a errores HTTP con sentido (409, 404...).

---

### 8.12 Resultado de los ejercicios (revisión)

Todos los casos se han probado contra la API (19-11-2026):

| Caso | Resultado | ¿Bien? |
|---|---|---|
| 4.1 POST correcto | 201 + `id`, `activo`, `creado_en` | ✅ |
| 4.2 email inválido | 422, `loc: ["body","email"]` | ✅ |
| 4.3 `nombre: ""` | 422, `string_too_short` | ✅ |
| 4.4 email repetido | **500** · `UniqueViolation` | ⏳ lección 9 → **409** |
| 4.5 campo de más (`"id": 999`) | 201, el `id` se **ignora** (lo pone Postgres) | ✅ (bonus: `extra="forbid"`) |
| 5.1 `{"activo": false}` | 200, solo cambia `activo` | ✅ |
| 5.2 `{}` | 200, no cambia nada | ✅ |
| 5.3 id que no existe | 404 | ✅ |
| 5.4 `{"nombre": ""}` | 1ª vuelta: **200 y nombre vacío** · 2ª: sigue igual (errata `lenght`, ver abajo) | ❌ → arreglar |
| 5.x `{"email": "no-es-email"}` | 1ª vuelta: **200 y email inválido** · 2ª: 422 (`EmailStr`) | ✅ |
| 5.5 email de otro usuario | **500** · `UniqueViolation` | ⏳ lección 9 → **409** |
| 6 DELETE | 1ª vuelta: la app **no arranca** (`response_model` + 204) · 2ª: **200** + el usuario borrado; repetido → 404 | ✅ (opción "200 + lo borrado") |
| 6.3 borrar a Luis (tiene pedidos) | **500** · `ForeignKeyViolation` | ⏳ lección 9 → **409** |
| 7.1 pedido correcto | 201, `importe: "12.50"` | ✅ |
| 7.2 `importe: -5` | 422 `greater_than_equal` (Pydantic) | ✅ |
| 7.3 `importe: 10.999` | 422 `decimal_max_places` (Pydantic) | ✅ |
| 7.x `producto: ""` | 1ª vuelta: **201 con producto vacío** · 2ª: 422 | ✅ |
| 7.4 usuario que no existe | 404 (gracias al `SELECT 1` previo) | ✅ |

**Lección de los ❌ (5.4, 5.x y 7.x): el modelo de entrada del PATCH necesita las
mismas reglas que el del POST.** `UsuarioActualizar` tenía `nombre: str | None` y
`email: str | None` sin `Field` ni `EmailStr`. Así que lo que el POST rechaza, el
PATCH lo deja pasar: basta con crear un usuario bien y luego "editarlo" mal.
Postgres tampoco lo para: `NOT NULL` no impide un texto vacío `''` (no es `NULL`).

```python
class UsuarioActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    activo: bool | None = None
```

> 💡 Regla: cada campo tiene **las mismas reglas** en todos los modelos de
> entrada donde aparece. En `...Actualizar` solo cambia que es opcional.

**Segunda vuelta del arreglo: dos trampas de `Field`** (comprobadas). El primer
intento fue:

```python
nombre: str | None = Field(min_lenght=1, max_lenght=100)    # ❌ dos fallos
```

| Fallo | Qué pasa | Por qué |
|---|---|---|
| Falta `default=None` | `PATCH {"activo": false}` → **422 `missing` `nombre`**: el campo se ha vuelto **obligatorio** | `Field(...)` ocupa el sitio del valor por defecto (8.2c). Si no le pasas `default=`, el campo **no tiene** valor por defecto → obligatorio. `str \| None` solo dice que *puede* valer `null`, no que pueda faltar (8.2b) |
| `lenght` en vez de `length` | `PATCH {"nombre": ""}` → **200** y nombre vacío: la regla **no se aplica** | `Field` no da error con un nombre que no conoce: lo guarda como dato extra y lo ignora. Solo avisa con un *warning* al arrancar: `PydanticDeprecatedSince20: Using extra keyword arguments on Field is deprecated... (Extra keys: 'min_lenght', 'max_lenght')` |

> 💡 Si en el arranque de `fastapi dev` aparece `Extra keys: '...'`, tienes una
> errata en un `Field`. Y **prueba siempre el caso que la regla debería parar**:
> que el caso bueno funcione no demuestra que la regla exista.

**Cómo se ve un 422 frente a un 500 en los ejercicios:**
- **422**: lo para **Pydantic**, antes de ejecutar tu función. El body dice
  qué campo y por qué. No se toca la base de datos.
- **500 con `psycopg.errors....`**: lo para **Postgres** (`UNIQUE`, FK...). Tu
  función sí se ejecutó, el `INSERT`/`UPDATE`/`DELETE` falló, y `get_conn` hizo
  `ROLLBACK`. El cliente no sabe qué ha pasado: eso lo arregla la lección 9.


---

## Lección 9 — Errores, códigos HTTP y paginación

### 9.0 El mapa

En la lección 8 quedaron tres casos que responden **500**:

| Caso | Excepción | Qué ha pasado de verdad |
|---|---|---|
| Crear o editar con un email repetido | `UniqueViolation` | El **cliente** pidió algo que choca con lo que hay |
| Borrar un usuario con pedidos | `ForeignKeyViolation` | El **cliente** pidió algo que la base de datos no permite |
| Crear un pedido justo cuando borran al usuario | `ForeignKeyViolation` | El usuario ya **no existe** |

Un 500 dice "**mi** código ha fallado", pero en los tres casos el código está
bien: Postgres ha hecho su trabajo (`UNIQUE`, FK) y ha parado algo que el
cliente no debía hacer. El problema es que **nadie traduce** ese "no" de Postgres
a un código HTTP. Esta lección va de esa traducción:

```
Postgres dice "no" (excepción de psycopg)
  └─▶ tu código la captura (try/except o un handler global)
        └─▶ la convierte en HTTPException(409 / 404, "mensaje claro")
              └─▶ el cliente recibe un 4xx y sabe qué ha hecho mal
```

Y al final, **paginación**: no devolver la tabla entera en cada `GET /usuarios`.

---

### 9.1 Qué código usar: la culpa y el motivo

La primera cifra dice **de quién es la culpa**; las otras dos, **el motivo**:

| Código | Cuándo | En nuestra API |
|---|---|---|
| **400** Bad Request | Petición mal hecha, en general | Casi no lo usarás: FastAPI ya da 422 para los datos mal formados |
| **401** Unauthorized | No sé **quién eres** (falta login o token) | Lección de autenticación |
| **403** Forbidden | Sé quién eres, pero **no puedes** | Ídem |
| **404** Not Found | Lo que pides **no existe** | `GET /usuarios/999`, pedido para un usuario que no existe |
| **409** Conflict | Los datos son válidos, pero **chocan con el estado actual** | Email repetido, borrar un usuario con pedidos |
| **422** Unprocessable Content | Los datos **no cumplen el formato** | Pydantic: email inválido, `importe: -5` |
| **500** Internal Server Error | **Bug tuyo**: algo que no habías previsto | Excepción sin capturar |
| **503** Service Unavailable | El servidor no puede atender **ahora** | La base de datos está caída |

**422 o 409, la duda típica:**
- **422** = "lo que mandas está **mal en sí mismo**". Lo sabes **sin mirar la base
  de datos**: `"no-es-email"` es inválido ahora y siempre.
- **409** = "lo que mandas está bien, pero **choca con lo que ya hay**". Solo lo
  sabes **mirando la base de datos**: `luis@mail.com` es un email perfecto, pero ya
  está cogido. Si Luis se borra, el mismo body funcionaría.

> 💡 Regla: un **500** en producción siempre es un bug que hay que arreglar. Los
> errores previsibles ("no existe", "repetido", "tiene hijos") tienen que salir
> como **4xx**, con un mensaje que le diga al cliente qué hacer.

---

### 9.2 Repaso de Python: `try` / `except`

Las excepciones **suben** por las funciones hasta que alguien las captura. Si
nadie lo hace, llegan a FastAPI, que responde 500.

```python
try:
    resultado = 10 / divisor          # código que puede fallar
except ZeroDivisionError:             # si falla CON ESTE TIPO de error...
    resultado = 0                     # ...se ejecuta esto, y el programa sigue
```

| Pieza | Qué hace |
|---|---|
| `try:` | "Intenta esto" |
| `except Tipo:` | Si dentro del `try` salta una excepción **de ese tipo** (o de un tipo hijo), entra aquí. Si es de otro tipo, **no** la captura y sigue subiendo |
| `except Tipo as e:` | Igual, pero guarda la excepción en `e` para mirar sus datos |
| `raise OtraCosa(...)` dentro del `except` | **Traducir**: cambiar una excepción por otra. Es lo que haremos: `UniqueViolation` → `HTTPException(409)` |

**Las excepciones son clases con herencia** (7.1b). Las de psycopg forman un
árbol (comprobado con `type(e).__mro__`):

```
Exception
 └─ psycopg.Error
     └─ DatabaseError
         └─ IntegrityError               ← "se ha roto una regla de integridad"
             ├─ UniqueViolation          ← UNIQUE / PRIMARY KEY repetido
             ├─ ForeignKeyViolation      ← FK
             ├─ CheckViolation           ← CHECK
             └─ NotNullViolation         ← NOT NULL
```

`except IntegrityError:` captura las cuatro de golpe; `except UniqueViolation:`
solo esa. **Captura siempre lo más concreto posible**: si capturas
`Exception`, te tragas también tus bugs, y un 500 que debía avisarte se
convierte en un 409 falso.

---

### 9.3 Capturar el error de Postgres en el endpoint → 409

```python
from psycopg import errors

@app.post("/usuarios", response_model=UsuarioLeer, status_code=201)
def crear_usuario(usuario: UsuarioCrear, conn: Conn):
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                INSERT INTO usuarios (nombre, email)
                VALUES (%(nombre)s, %(email)s)
                RETURNING id, nombre, email, activo, creado_en
            """, usuario.model_dump())
            return cur.fetchone()
    except errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese email")
```

Comprobado: `POST {"nombre": "D", "email": "luis@mail.com"}` →
`409 {"detail": "Ya existe un usuario con ese email"}`.

| Pieza | Qué hace |
|---|---|
| `from psycopg import errors` | El módulo con **una clase por cada error de Postgres** (`errors.UniqueViolation`, `errors.ForeignKeyViolation`...) |
| `try:` alrededor del `with` | Solo envuelve el código que puede chocar con la base de datos |
| `except errors.UniqueViolation:` | Solo este error. Un error de sintaxis SQL (un bug tuyo) **no** entra aquí y sigue dando 500, que es lo correcto |
| `raise HTTPException(409, ...)` | La traducción. Esta excepción sube por `get_conn` → **`ROLLBACK`** → FastAPI responde 409 |

**¿Y la transacción?** Tras un error, Postgres marca la transacción como **rota**
(el `curso=!#` de `psql`, lección 4.5). Aquí no importa: el `HTTPException` sale
de la función, `get_conn` hace `ROLLBACK` y la conexión vuelve limpia al pool.
Lo que **no** puedes hacer es capturar el error y **seguir usando la conexión**
(comprobado):

```python
try:
    conn.execute("INSERT ... 'luis@mail.com'")
except errors.UniqueViolation:
    pass                       # ❌ "me lo trago y sigo"
conn.execute("SELECT 1")
# psycopg.errors.InFailedSqlTransaction: current transaction is aborted,
#   commands ignored until end of transaction block   → 500
```

Es el mismo `curso=!#` de `psql`: hasta el `ROLLBACK`, todo lo demás falla. Por eso
la regla es **capturar y salir** (`raise HTTPException`), no capturar y continuar.

#### Saber **qué** regla se ha roto: `e.diag`

Si una tabla tiene **varios** `UNIQUE` (email y DNI, por ejemplo), los dos dan
`UniqueViolation`. Para dar el mensaje correcto, mira cuál ha sido:

```python
except errors.UniqueViolation as e:
    if e.diag.constraint_name == "usuarios_email_key":
        raise HTTPException(409, "Ya existe un usuario con ese email")
    raise                       # otro UNIQUE que no esperaba → que siga subiendo (500)
```

| Atributo | Ejemplo (comprobado) | Qué es |
|---|---|---|
| `e.diag.constraint_name` | `"usuarios_email_key"` | El **nombre de la restricción** (lo ves en `\d usuarios`) |
| `e.sqlstate` | `"23505"` | El código de error estándar de SQL. `23505` = unique, `23503` = FK, `23514` = check, `23502` = not null |

`raise` a secas dentro de un `except` = "**vuelve a lanzar** la misma excepción":
no sé qué hacer con ella, que siga subiendo.

---

### 9.4 ¿Comprobar antes o intentar y capturar?

En el ejercicio 7 hiciste "**comprobar antes**": `SELECT 1` y, si no existe, 404.
La alternativa es "**intentar y capturar**": hacer el `INSERT` directamente y, si
salta la FK, 404.

```python
# A) Comprobar antes (lo que hiciste)
cur.execute("SELECT 1 FROM usuarios WHERE id = %s", (usuario_id,))
if cur.fetchone() is None:
    raise HTTPException(404, "Usuario no encontrado")
cur.execute("INSERT INTO pedidos ...")

# B) Intentar y capturar
try:
    cur.execute("INSERT INTO pedidos ...")
except errors.ForeignKeyViolation:
    raise HTTPException(404, "Usuario no encontrado")
```

| | A) Comprobar antes | B) Intentar y capturar |
|---|---|---|
| Consultas | 2 | 1 |
| Se lee | Muy claro | Hay que saber qué FK puede saltar |
| **Carrera** (*race condition*) | Entre el `SELECT` y el `INSERT` otra petición puede borrar al usuario → la FK salta igual → **500** | No hay hueco: la comprobación **es** el `INSERT` |

**La conclusión importante:** aunque compruebes antes, la restricción de Postgres
puede saltar igual (dos peticiones a la vez). Con el email pasa lo mismo: si
haces `SELECT ... WHERE email = ...` antes de insertar, dos `POST` simultáneos
con el mismo email pueden pasar los dos el `SELECT`, y uno choca con el `UNIQUE`.
**La única fuente de verdad es la restricción de la base de datos**, y su
excepción hay que capturarla siempre. Comprobar antes es opcional; capturar, no.

---

### 9.5 Un handler global: traducir en **un solo sitio**

Si diez endpoints pueden dar `ForeignKeyViolation`, poner diez `try/except` es
repetir código. FastAPI deja registrar una función que **traduce un tipo de
excepción en toda la app**:

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from psycopg import errors

@app.exception_handler(errors.ForeignKeyViolation)
def fk_violation(request: Request, exc: errors.ForeignKeyViolation):
    return JSONResponse(
        status_code=409,
        content={"detail": "La operación choca con datos relacionados"},
    )
```

Comprobado: `DELETE /usuarios/1` (Luis, con pedidos) → **409** sin tocar el
endpoint del DELETE.

#### Cómo se usa: **no lo llamas tú**

Un handler es como un endpoint: lo **registras** con un decorador y FastAPI lo
llama solo cuando toca. Nunca escribes `fk_violation(...)` en ningún sitio.

**Dónde va:** en `main.py`, **después** de `app = FastAPI(...)` (el decorador
necesita que `app` exista) y normalmente **antes** de los endpoints:

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from psycopg import errors
...

app = FastAPI(lifespan=lifespan)

# ── handlers de errores ──────────────────────────────────────────
@app.exception_handler(errors.ForeignKeyViolation)
def fk_violation(request: Request, exc: errors.ForeignKeyViolation):
    return JSONResponse(
        status_code=409,
        content={"detail": "La operación choca con datos relacionados"},
    )

# ── endpoints ────────────────────────────────────────────────────
@app.delete("/usuarios/{usuario_id}", status_code=204)
def borrar_usuario(usuario_id: int, conn: Conn):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))   # ← sin try/except
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
```

El endpoint **no sabe nada** del handler: se escribe como si el error no
existiera. Lo que pasa con `DELETE /usuarios/1`:

```
1. borrar_usuario ejecuta el DELETE
2. Postgres: "Luis tiene pedidos" → psycopg lanza ForeignKeyViolation
3. nadie la captura en el endpoint → sube...
4. ...pasa por get_conn → ROLLBACK
5. llega a FastAPI. ¿Hay un handler para ForeignKeyViolation? Sí → llama a fk_violation(request, exc)
6. fk_violation devuelve un JSONResponse → eso es lo que recibe el cliente:
     HTTP/1.1 409 Conflict
     {"detail": "La operación choca con datos relacionados"}
```

Sin el handler, en el paso 5 FastAPI no encuentra a nadie y responde **500**.

**Qué excepciones atrapa:** las del tipo indicado **y sus hijas** (9.2). Así que:

| Registras | Atrapa |
|---|---|
| `errors.ForeignKeyViolation` | Solo los fallos de FK |
| `errors.IntegrityError` | FK, `UNIQUE`, `CHECK` y `NOT NULL` |

Puedes registrar **varios** handlers, uno por tipo. Si hay uno para el hijo y
otro para el padre, gana el **más concreto**.

**Usar `exc` para afinar el mensaje:** el handler recibe la excepción, así que
puede mirar qué restricción saltó (9.3):

```python
@app.exception_handler(errors.ForeignKeyViolation)
def fk_violation(request: Request, exc: errors.ForeignKeyViolation):
    if exc.diag.constraint_name == "pedidos_usuario_id_fkey":
        mensaje = "El usuario tiene pedidos o no existe"
    else:
        mensaje = "La operación choca con datos relacionados"
    return JSONResponse(status_code=409, content={"detail": mensaje})
```

| Pieza | Qué hace |
|---|---|
| `@app.exception_handler(Tipo)` | "Cuando una excepción de este tipo llegue sin capturar hasta FastAPI, llama a esta función en vez de responder 500" |
| `request: Request` | La petición que falló (aquí no la usamos, pero FastAPI la pasa siempre) |
| `exc` | La excepción: puedes mirar `exc.diag.constraint_name` |
| `JSONResponse(...)` | Un handler no puede lanzar `HTTPException`: tiene que **devolver la respuesta** directamente. `content=` es el body; usa `{"detail": ...}` para que tenga la misma forma que los demás errores |

**El `ROLLBACK` sigue ocurriendo**: la excepción pasa primero por `get_conn`
(`scope="function"`) y después llega al handler.

**¿Handler global o `try/except` en el endpoint?**

| | `try/except` en el endpoint | Handler global |
|---|---|---|
| Mensaje | **Específico**: "Ya existe un usuario con ese email" | **Genérico**: no sabe qué endpoint era |
| Código | Puede ser distinto por endpoint (404 al crear pedido, 409 al borrar usuario) | El mismo para todos |
| Repetición | Uno por endpoint | Uno para toda la app |

Lo habitual es **las dos cosas**: `try/except` donde quieres un mensaje concreto,
y un handler global como **red de seguridad** para los casos que se te pasen. Si
el endpoint captura la excepción, el handler global ya no la ve.

---

### 9.6 Paginación: `LIMIT` y `OFFSET`

`GET /usuarios` devuelve **toda** la tabla. Con 6 filas da igual; con 2 millones
tumbas la API, la base de datos y el navegador. Se devuelve **por páginas**.

**En SQL:**

```sql
SELECT ... FROM usuarios ORDER BY id LIMIT 2 OFFSET 0;   -- página 1: filas 1-2
SELECT ... FROM usuarios ORDER BY id LIMIT 2 OFFSET 2;   -- página 2: filas 3-4
SELECT ... FROM usuarios ORDER BY id LIMIT 2 OFFSET 4;   -- página 3: filas 5-6
```

| Pieza | Qué hace |
|---|---|
| `LIMIT n` | Devuelve **como mucho** `n` filas |
| `OFFSET m` | Se **salta** las `m` primeras |
| `ORDER BY` | **Obligatorio** en la práctica. Sin él, Postgres no garantiza ningún orden, y la "página 2" podría repetir filas de la 1 o saltarse alguna |

**En la API**, `limite` y `offset` llegan por la consulta (`?limite=2&offset=2`), y
hay que **ponerles límites**. Si no, `?limite=10000000` vuelve a tumbarlo todo:

```python
from typing import Annotated
from fastapi import Query

@app.get("/usuarios", response_model=list[UsuarioLeer])
def listar_usuarios(
    conn: Conn,
    limite: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT id, nombre, email, activo, creado_en
            FROM usuarios
            ORDER BY id
            LIMIT %(limite)s OFFSET %(offset)s
        """, {"limite": limite, "offset": offset})
        return cur.fetchall()
```

| Pieza | Qué hace |
|---|---|
| `Query(ge=1, le=100)` | Lo mismo que `Field` (8.2c), pero para parámetros **de la consulta**. `?limite=500` → **422** `Input should be less than or equal to 100` (comprobado) |
| `Annotated[int, Query(...)]` | El mismo `Annotated` de `Conn` (7.5): tipo + metadato |
| `= 20` | Valor por defecto: sin `?limite`, 20 |
| `LIMIT %(limite)s` | `LIMIT` y `OFFSET` son **valores**, así que van con marcador como cualquier otro (7.7) |

#### Devolver también el total

Para pintar "Página 2 de 5", el cliente necesita saber **cuántos hay en total**.
Se devuelve un objeto que envuelve la lista:

```json
{"items": [{"id": 3, ...}, {"id": 4, ...}], "total": 6, "limite": 2, "offset": 2}
```

```python
class PaginaUsuarios(BaseModel):
    items: list[UsuarioLeer]
    total: int
    limite: int
    offset: int
```

El total es otra consulta: `SELECT count(*) AS total FROM usuarios` (con el mismo
`WHERE` que el listado, si lo hay).

> 💡 **`OFFSET` se vuelve lento con tablas enormes**: para dar la página 10.000,
> Postgres tiene que leer y descartar todas las filas anteriores. La alternativa
> es la **paginación por cursor** (*keyset*): "dame 20 a partir del id 4.381" →
> `WHERE id > %s ORDER BY id LIMIT 20`, que usa el índice y va igual de rápido en
> cualquier página. Para listados de una aplicación interna, `LIMIT`/`OFFSET` va
> de sobra.

#### Filtros opcionales: `NULL` como "no filtres"

`?activo=true` → solo activos; sin `?activo` → todos. Con un solo SQL:

```python
activo: bool | None = None
...
WHERE (%(activo)s::boolean IS NULL OR activo = %(activo)s)
```

- Si no viene, `activo` es `None` → `NULL IS NULL` es cierto → el `WHERE` deja pasar todo.
- Si viene, la primera parte es falsa y manda la segunda: `activo = true`.
- **El `::boolean` es obligatorio** (comprobado). Sin él, Postgres recibe un
  `NULL` suelto y no sabe de qué tipo es:
  `psycopg.errors.AmbiguousParameter: could not determine data type of parameter $1` → 500.
  `::tipo` es el *cast* de Postgres: "trata esto como un booleano".

---

### 9.7 ✏️ Ejercicios de la lección 9

**Ejercicio 1: email repetido → 409**
En `POST /usuarios` y `PATCH /usuarios/{id}`, captura `UniqueViolation` y responde
**409** `"Ya existe un usuario con ese email"`. Pruébalo con `luis@mail.com` en los
dos.
❓ Si un día añades otra columna `UNIQUE`, ¿qué mensaje saldría? ¿Cómo lo evitas? (9.3, `e.diag`)

**Ejercicio 2: borrar un usuario con pedidos → 409**
`DELETE /usuarios/1` (Luis) → **409** `"El usuario tiene pedidos"`. Hazlo con
`try/except` en el endpoint.

**Ejercicio 3: pedido para un usuario que no existe → "intentar y capturar"**
Reescribe `POST /usuarios/{usuario_id}/pedidos` **sin** el `SELECT 1`: haz el
`INSERT` directamente y convierte `ForeignKeyViolation` en **404**. Comprueba que
`/usuarios/999/pedidos` sigue dando 404.
❓ ¿Por qué esta versión no tiene el problema de la carrera? (9.4)

**Ejercicio 4: red de seguridad global**
Añade un `@app.exception_handler(errors.IntegrityError)` que responda **409**
`{"detail": "Conflicto con los datos existentes"}`.
Para probarlo, **comenta** temporalmente el `try/except` del ejercicio 2 y repite
`DELETE /usuarios/1`. ¿Sale el mensaje del handler? Vuelve a descomentarlo: ¿cuál
gana ahora, y por qué?

**Ejercicio 5: paginación**
`GET /usuarios?limite=2&offset=0` → los 2 primeros. Devuelve el objeto
`PaginaUsuarios` con `items`, `total`, `limite` y `offset`. Pruébalo con:
1. Sin parámetros → defecto `limite=20`, `offset=0`.
2. `?limite=2&offset=2` → ¿qué ids salen?
3. `?offset=100` → ¿qué devuelve? ¿Es un 404? (8.5: lista vacía ≠ no existe)
4. `?limite=0`, `?limite=500`, `?offset=-1` → 422.

**Ejercicio 6: filtro opcional**
Añade `?activo=true|false` al listado del ejercicio 5. El `total` tiene que
contar **con el mismo filtro**: con `?activo=false`, ¿cuánto vale `total`?
Prueba primero **sin** el `::boolean` para ver el error.

**🎯 Bonus: paginar los pedidos**
Aplica la paginación a `GET /usuarios/{usuario_id}/pedidos`. ¿Qué pasa con el 404
si el usuario existe pero `offset` se sale de sus pedidos?

> 💡 Al acabar, **ningún** caso de los ejercicios de la lección 8 debería dar 500.
> Repasa la tabla de 8.12: los ⏳ tienen que pasar a 409 o 404.

---

### 9.8 📋 Chuleta: errores de psycopg → código HTTP

Postgres tiene **cientos** de errores, pero en una API te vas a encontrar unos 30.
Cada error de Postgres trae un **SQLSTATE**: un código de 5 caracteres que es
estándar de SQL. Las **dos primeras cifras son la familia** (`23` = integridad,
`42` = tu SQL está mal...). psycopg tiene **una clase por código**, y cada clase
hereda de una **clase padre** según su familia. Los nombres y la herencia de
estas tablas están sacados del propio psycopg instalado (`errors.lookup("23505")`).

#### El árbol de familias

```
psycopg.Error
├─ InterfaceError         ← error de psycopg, no de Postgres (cursor cerrado...)
└─ DatabaseError
    ├─ IntegrityError     ← 23xxx: se ha roto una restricción (UNIQUE, FK, CHECK, NOT NULL)
    ├─ DataError          ← 22xxx: un valor no vale para su tipo (texto largo, número enorme...)
    ├─ ProgrammingError   ← 42xxx: el SQL está mal o no tienes permiso (bug o configuración)
    ├─ OperationalError   ← 08, 28, 40, 53, 57xxx: problemas de conexión, bloqueos, servidor caído
    └─ InternalError      ← 25xxx: estado de la transacción (rota, solo lectura...)
```

La pregunta clave para elegir el código HTTP es siempre la de 9.1: **¿de quién es
la culpa?** Si es del cliente → 4xx. Si es tuya → 500 (y se arregla el código). Si
es de la infraestructura → 503.

#### 23 · `IntegrityError`: restricciones → **casi siempre culpa del cliente**

| SQLSTATE | `errors.` | Cuándo salta | HTTP |
|---|---|---|---|
| `23505` | `UniqueViolation` | `UNIQUE` o `PRIMARY KEY` repetido: email que ya existe | **409** |
| `23503` | `ForeignKeyViolation` | Borrar un padre con hijos (Luis con pedidos) | **409** |
| `23503` | `ForeignKeyViolation` | Crear un hijo que apunta a un padre que no existe (pedido para el usuario 999) | **404** |
| `23502` | `NotNullViolation` | Un `NULL` en columna `NOT NULL` | **422** si viene del cliente · **500** si es un bug tuyo (te olvidaste una columna en el `INSERT`) |
| `23514` | `CheckViolation` | Un `CHECK` (`importe >= 0`) | **422**. Si llega aquí es que a tu modelo Pydantic le falta la regla: añádela |
| `23P01` | `ExclusionViolation` | `EXCLUDE` (p. ej. dos reservas de la misma sala que se solapan) | **409** |

#### 22 · `DataError`: el valor no cabe en su tipo → **cliente, o validación que te falta**

| SQLSTATE | `errors.` | Cuándo salta (mensaje real) | HTTP |
|---|---|---|---|
| `22001` | `StringDataRightTruncation` | Texto más largo que un `varchar(n)`: `value too long for type character varying(100)` | **422** (pon `max_length` en Pydantic) |
| `22003` | `NumericValueOutOfRange` | Número que no cabe: `numeric field overflow` (`99999999999` en `numeric(10,2)`) | **422** (pon `max_digits`) |
| `22P02` | `InvalidTextRepresentation` | Texto que no se puede convertir: `invalid input syntax for type integer: "abc"` | **422** · normalmente Pydantic lo para antes |
| `22007` | `InvalidDatetimeFormat` | Fecha con formato inválido | **422** |
| `22008` | `DatetimeFieldOverflow` | Fecha imposible (`2026-02-30`) | **422** |
| `22012` | `DivisionByZero` | `division by zero` en tu SQL | **500** (bug: protege la división) |

> 💡 Si un `DataError` o un `CheckViolation` llegan a Postgres, casi siempre
> significa que **a tu modelo Pydantic le falta una regla**. Lo ideal es que el
> cliente reciba un 422 de Pydantic y Postgres no llegue a quejarse.

#### 42 · `ProgrammingError`: tu SQL o tus permisos → **siempre 500**

Ninguno es culpa del cliente: **no los traduzcas**, arréglalos.

| SQLSTATE | `errors.` | Cuándo salta | Qué hacer |
|---|---|---|---|
| `42601` | `SyntaxError` | SQL mal escrito (`WHERE id == %s`, `JOIN` sin `ON`) | Arreglar el SQL |
| `42P01` | `UndefinedTable` | Tabla que no existe (errata, o schema equivocado) | Revisar nombre y `search_path` |
| `42703` | `UndefinedColumn` | Columna que no existe | Revisar nombre (`\d tabla`) |
| `42883` | `UndefinedFunction` | Función u operador que no existe para esos tipos (`operator does not exist`) | Revisar tipos, a veces falta un `::tipo` |
| `42702` | `AmbiguousColumn` | Con `JOIN`, `id` sin decir de qué tabla | Prefijo: `u.id` |
| `42P08` | `AmbiguousParameter` | Un `%s` cuyo tipo Postgres no puede deducir (`%(activo)s IS NULL`) | Añadir `::tipo` (9.6) |
| `42P18` | `IndeterminateDatatype` | Parecido: no puede deducir el tipo de un parámetro | Añadir `::tipo` |
| `42501` | `InsufficientPrivilege` | `permission denied for table ...` | `GRANT` al rol de la API (8.10). **No** es un 403: el cliente no ha hecho nada mal, es **tu** configuración |
| `3D000` | `InvalidCatalogName` | La base de datos de la URL no existe | Revisar `DATABASE_URL` |

#### 25 · `InternalError`: estado de la transacción

| SQLSTATE | `errors.` | Cuándo salta | HTTP |
|---|---|---|---|
| `25P02` | `InFailedSqlTransaction` | Seguir usando la conexión tras un error: `current transaction is aborted` (9.3) | **500** (bug: captura y **sal**, no sigas) |
| `25006` | `ReadOnlySqlTransaction` | Escribir en una réplica de solo lectura o en una transacción `READ ONLY` | **500** (configuración) |

#### 40 / 55 / 57 / 53 / 08 / 28 · `OperationalError`: la infraestructura → **503** o reintentar

| SQLSTATE | `errors.` | Cuándo salta | HTTP |
|---|---|---|---|
| `40001` | `SerializationFailure` | Dos transacciones chocan en aislamiento `SERIALIZABLE` | **Reintentar** la transacción; si sigue, 503 |
| `40P01` | `DeadlockDetected` | Interbloqueo: dos transacciones se esperan mutuamente | **Reintentar**; si sigue, 503 |
| `55P03` | `LockNotAvailable` | `SELECT ... FOR UPDATE NOWAIT` y la fila está bloqueada | **409** o reintentar |
| `57014` | `QueryCanceled` | La consulta superó el `statement_timeout` | **503** (o 504) |
| `57P01` | `AdminShutdown` | Postgres se está apagando / reiniciando | **503** |
| `57P03` | `CannotConnectNow` | Postgres está arrancando | **503** |
| `53300` | `TooManyConnections` | Se alcanzó `max_connections` | **503** (revisa el `max_size` del pool) |
| `53100` | `DiskFull` | Sin espacio en disco | **503** |
| `08006` | `ConnectionFailure` | Se cortó la conexión a mitad | **503** |
| `28P01` | `InvalidPassword` | Contraseña mala | Configuración (`.env`) |

> ⚠️ **Al conectar, psycopg no usa estas subclases** (comprobado): tanto con el
> servidor apagado como con contraseña mala lanza un `psycopg.OperationalError`
> genérico, con `sqlstate = None` y el motivo solo en el mensaje
> (`password authentication failed...`, `Is the server running...?`). Para
> "la base de datos no está disponible", captura `psycopg.OperationalError`.

#### ⚠️ "No existe" **no es un error** para Postgres → el 404 lo pones tú

Un `UPDATE`, `DELETE` o `SELECT` con un `WHERE id = 999` que no encuentra nada
**no lanza ninguna excepción**. Para Postgres, "he actualizado 0 filas" es un
resultado perfectamente válido (en `psql` verías `UPDATE 0`). Por eso **no hay
ninguna clase de psycopg que capturar**: tienes que **preguntar** cuántas filas
se han tocado y lanzar tú el 404.

| Sentencia | Cómo detectas "no existía" | Lo viste en |
|---|---|---|
| `SELECT ... WHERE id = %s` | `cur.fetchone()` devuelve `None` | 7.8 |
| `UPDATE ... RETURNING ...` (PATCH) | `cur.fetchone()` devuelve `None` | 8.7 |
| `DELETE ...` sin `RETURNING` | `cur.rowcount == 0` | 8.8 |
| `DELETE ... RETURNING ...` | `cur.fetchone()` devuelve `None` | 8.12 (tu DELETE) |
| `INSERT` de un hijo con un padre que no existe | **Aquí sí** hay excepción: `ForeignKeyViolation` | 9.4 |

```python
# PATCH: el UPDATE no falla, simplemente no devuelve fila
usuario = cur.fetchone()          # None si ningún usuario tenía ese id
if usuario is None:
    raise HTTPException(status_code=404, detail="Usuario no encontrado")
```

**La regla:** una excepción de psycopg = Postgres ha dicho "**no puedo**" (choca
con una regla). Un resultado vacío = Postgres ha dicho "**hecho, y no había
nada**". El primero se **captura**; el segundo se **comprueba**.

#### Errores que **no** vienen de Postgres

| Excepción | Cuándo salta | Ejemplo del curso | HTTP |
|---|---|---|---|
| `psycopg.InterfaceError` | Usar algo ya cerrado | `the cursor is closed` (8.6) | **500** (bug) |
| `psycopg.ProgrammingError` (sin SQLSTATE) | psycopg rechaza tu consulta antes de enviarla | `%(activo)` sin la `s` (8.6) | **500** (bug) |
| `TypeError` | Parámetros mal pasados | `object of type 'int' has no len()` (7.11) | **500** (bug) |
| `psycopg_pool.PoolTimeout` | Ninguna conexión libre en el pool tras esperar | Muchas peticiones lentas a la vez | **503** |

#### Cómo averiguar cualquier otro

```python
from psycopg import errors

errors.lookup("23505")          # → <class 'psycopg.errors.UniqueViolation'>

try:
    ...
except psycopg.Error as e:
    print(type(e).__name__, e.sqlstate, e.diag.constraint_name)   # qué es, su código, qué restricción
```

La lista **completa** de códigos está en la documentación de Postgres:
*Appendix A. PostgreSQL Error Codes*. El nombre de la clase de psycopg es el
nombre del apéndice en *CamelCase* (`unique_violation` → `UniqueViolation`).

**Resumen en una línea por familia:**

| Familia | Padre | Culpa | HTTP típico |
|---|---|---|---|
| `23` | `IntegrityError` | Cliente | 409 / 404 / 422 |
| `22` | `DataError` | Cliente (o te falta validar) | 422 |
| `42` | `ProgrammingError` | **Tuya** | 500: arréglalo |
| `25` | `InternalError` | Tuya | 500 |
| `40`, `53`, `57`, `08` | `OperationalError` | Infraestructura | 503 / reintentar |

---

## Anexo: problemas del entorno (WSL + Docker Desktop)

### Autocompletado de `docker` con TAB lentísimo (~3,5 s)

**Cómo funciona el autocompletado:** el script
`/usr/share/bash-completion/completions/docker` no sabe nada por sí mismo; en
cada TAB ejecuta `docker __complete ...` y es el propio `docker` quien responde.
Para responder, `docker` arranca **todos sus plugins** (`compose`, `buildx`,
`scout`...) para preguntarles qué comandos ofrecen.

**Diagnóstico (midiendo, no adivinando):**

```bash
time docker __complete ps ''      # 3,4 s  ← lento
# medir cada plugin por separado:
~/.docker/cli-plugins/docker-scout docker-cli-plugin-metadata   # 3,3 s  ← culpable
/usr/local/lib/docker/cli-plugins/docker-scout docker-cli-plugin-metadata  # 0,5 s
```

**Causa:** un enlace viejo `~/.docker/cli-plugins/docker-scout` apuntaba a
`/mnt/c/...`, es decir, al **disco de Windows**. Leer ficheros de Windows desde
WSL es muy lento, y este binario pesa ~190 MB. Además, la carpeta del usuario
tiene **prioridad** sobre la del sistema, así que Docker usaba la copia lenta
en vez de la buena.

**Arreglo:** borrar el enlace. `rm` sobre un enlace simbólico borra solo el
enlace, no el fichero de Windows:

```bash
rm ~/.docker/cli-plugins/docker-scout
```

> 💡 **Regla de WSL:** todo lo que esté en `/mnt/c/...` va lento. Proyectos,
> binarios y datos, mejor dentro de Linux (`/home/...`).

---

## Chuleta de comandos

_(se irá rellenando)_
