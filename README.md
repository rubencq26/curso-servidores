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
| 3 | SQL básico: tablas, tipos, claves, CRUD | ⏳ en curso |
| 4 | Relaciones: claves foráneas, JOINs, índices | ⬜ |
| 5 | Proyecto Python: entorno virtual, dependencias, variables de entorno | ⬜ |
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
`NOT NULL`, `UNIQUE`, `DEFAULT`...). Las vemos en la siguiente sección.

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
