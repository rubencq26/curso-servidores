# Curso: PostgreSQL + FastAPI desde cero

> Apuntes del curso. Cada lección añade una sección. Yo (Rubén) escribo el código;
> Claude revisa y explica.

**Entorno:** WSL2 (Ubuntu 24.04) · Python 3.12 · PostgreSQL en **Docker** (Docker Desktop en Windows)

---

## Temario

| # | Lección | Estado |
|---|---------|--------|
| 1 | Qué es un servidor PostgreSQL y levantarlo con Docker | ✅ |
| 2 | `psql`: conectarse, roles, bases de datos y permisos | ✅ |
| 3 | SQL básico: tablas, tipos, claves, CRUD | ✅ |
| 4 | Relaciones: claves foráneas, JOINs, índices | ✅ |
| 5 | Proyecto Python: entorno virtual, dependencias, variables de entorno | ⏳ en curso |
| 6 | FastAPI: primer endpoint, rutas, Swagger (`/docs`) | ⬜ |
| 7 | Conectar FastAPI con PostgreSQL (pool de conexiones) | ⬜ |
| 8 | CRUD completo con Pydantic (validación de entrada/salida) | ⬜ |
| 9 | Errores, códigos HTTP y paginación | ⬜ |
| 10 | Seguridad básica: SQL injection, credenciales, usuario de solo-lectura | ⬜ |
| 11 | Trabajar contra un Postgres que **ya existe** (el caso del trabajo) | ⬜ |

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
| `docker exec ... psql "postgresql://api_curso:...@localhost..."` | `host ... ::1/128 trust` | **No** (aunque pongas una mal, entra) |
| Desde WSL / tu API, por el puerto 5432 mapeado | Llega desde la red de Docker (`172.x.x.x`) → última regla, `scram-sha-256` | **Sí** |

> 💡 La imagen oficial de Docker confía en todo lo que viene **de dentro** del
> contenedor y pide contraseña a todo lo que viene **de fuera**. Para desarrollo
> está bien; en un servidor real, `trust` en red sería una barbaridad.
>
> En el trabajo **no** vais a tocar `pg_hba.conf` (es cosa del administrador), pero
> si os sale `no pg_hba.conf entry for host "x.x.x.x"...`, significa que **ninguna
> regla deja entrar desde vuestra IP**: hay que pedirle al admin que la añada.

```bash
# ver las reglas activas del contenedor (sin comentarios ni líneas vacías)
docker exec curso-postgres sh -c 'grep -v "^#" /var/lib/postgresql/data/pg_hba.conf | grep -v "^$"'
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

**El usuario de la API solo ve lo que se le ha dado:** `api_curso` tiene
`SELECT` en `usuarios`, pero **no** en `pedidos` → `permission denied for table pedidos`.
Lo del `\dp` de la lección 2 aplica igual desde Python.

**`.env` / `.env.example` / `.gitignore`:**
- `.env.example` con un **ejemplo del formato**, no vacío: quien clone el repo tiene que saber qué poner.
- Añadir `__pycache__/` al `.gitignore` **antes** de que aparezca (Python lo crea al importar módulos).
- Comprobar que git ignora un fichero: `git check-ignore -v .env`.

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
