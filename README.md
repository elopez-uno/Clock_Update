# ZKTeco Clock Sync

Sistema para sincronizar la fecha y hora de relojes biométricos ZKTeco cuando pierden la configuración por cortes de energía. Incluye interfaz web, base de datos MySQL y sincronización automática mediante cron.

## Estructura del Proyecto

```
UpdateClock/
├── .env                    # Variables de entorno (credenciales)
├── .gitignore             # Archivos a ignorar por git
├── docker-compose.yml     # Orquestación de contenedores
├── README.md              # Este archivo
├── app/                   # Aplicación web Python/Flask
│   ├── Dockerfile
│   ├── app.py             # Aplicación principal
│   ├── crontab            # Configuración de cron
│   ├── requirements.txt   # Dependencias Python
│   ├── templates/         # Plantillas HTML
│   └── scripts/           # Scripts auxiliares
├── mysql/                 # Contenedor MySQL
│   ├── Dockerfile
│   └── init/              # Scripts de inicialización
│       ├── 01-init.sql
│       └── 02-create-admin.sql
└── scripts/               # Script de sincronización para cron
    └── sync_clocks.py
```

## Características

- **Base de datos MySQL separada** en su propio contenedor Docker
- **Aplicación web Flask** para administrar relojes y usuarios
- **Sincronización manual** desde la interfaz web
- **Sincronización automática** mediante cron cada 15 minutos
- **Autenticación de usuarios** con contraseñas hasheadas (bcrypt)
- **CRUD completo** para relojes (IP, nombre/destino, ubicación, activo/inactivo)
- **Registro de logs** de todas las sincronizaciones
- **Usuario administrador pre-configurado**

## Requisitos Previos

- Docker
- Docker Compose
- Acceso a la red de los relojes ZKTeco

## Instalación y Configuración

### 1. Clonar o copiar el proyecto

Asegúrese de tener todos los archivos en el directorio `UpdateClock`.

### 2. Configurar variables de entorno

Edite el archivo `.env` según sus necesidades:

```env
# MySQL Root credentials
MYSQL_ROOT_PASSWORD=rootpassword
MYSQL_DATABASE=clock
MYSQL_USER=clock_user
MYSQL_PASSWORD=clock_password

# MySQL Docker
MYSQL_PORT=3306
MYSQL_HOST=mysql-db

# App Docker
APP_PORT=8080
APP_SECRET_KEY=change-this-secret-key-in-production

# Admin credentials for initial setup
ADMIN_USERNAME=admin
ADMIN_PASSWORD=Belgrano369*-
```

> **Importante:** Cambie `APP_SECRET_KEY` y las contraseñas por valores seguros en producción.

### 3. Iniciar los contenedores

Desde el directorio raíz del proyecto:

```bash
docker-compose up -d --build
```

Este comando:
- Construirá y levantará el contenedor MySQL (`zkteco-mysql`)
- Construirá y levantará el contenedor de la aplicación (`zkteco-app`)
- Inicializará la base de datos con las tablas necesarias
- Creará el usuario administrador
- Configurará cron para sincronización automática

### 4. Verificar el estado

```bash
docker-compose ps
```

Ambos contenedores deben estar en estado `Up` y `healthy` (MySQL).

### 5. Acceder a la aplicación

Abra su navegador en: `http://localhost:8080`

**Credenciales por defecto:**
- Usuario: `admin`
- Contraseña: `Belgrano369*-`

> **Recomendación:** Cambie la contraseña del administrador después del primer inicio de sesión.

## Uso de la Aplicación

### Panel Principal
Muestra el estado de todos los relojes registrados con su IP, ubicación y última actualización.

### Administrar Relojes (solo administradores)
1. Ir a "Relojes" > "Agregar Reloj"
2. Completar los campos:
   - **Nombre/Destino**: Identificación del reloj (ej: "Entrada Principal")
   - **Dirección IP**: IP del reloj ZKTeco en la red
   - **Ubicación**: Ubicación física (opcional)
   - **Activo**: Marcar si debe sincronizarse automáticamente
3. Guardar

### Sincronizar Manualmente
Desde el panel principal o desde administración de relojes, presione "Sincronizar" en el reloj deseado.

### Ver Logs
En "Logs" se pueden ver todos los intentos de sincronización con fecha, estado (Éxito/Fallido/Error) y mensaje.

### Administrar Usuarios (solo administradores)
Permite crear nuevos usuarios. Se puede asignar permisos de administrador.

## Sincronización Automática con Cron

El script `/app/scripts/sync_clocks.py` se ejecuta automáticamente cada 15 minutos mediante cron dentro del contenedor de la aplicación.

Para modificar la frecuencia, edite `app/crontab`:

```cron
# Cada 15 minutos
*/15 * * * * root cd /app && /usr/local/bin/python /app/scripts/sync_clocks.py >> /var/log/clock-sync.log 2>&1

# Cada hora
0 * * * * root cd /app && /usr/local/bin/python /app/scripts/sync_clocks.py >> /var/log/clock-sync.log 2>&1

# Cada 30 minutos
*/30 * * * * root cd /app && /usr/local/bin/python /app/scripts/sync_clocks.py >> /var/log/clock-sync.log 2>&1
```

Después de modificar, reconstruya el contenedor:

```bash
docker-compose up -d --build app
```

### Ver logs del cron
```bash
docker exec -it zkteco-app tail -f /var/log/clock-sync.log
```

### Ejecutar sincronización manualmente desde el contenedor
```bash
docker exec -it zkteco-app python /app/scripts/sync_clocks.py
```

## Estructura de la Base de Datos

### Tabla `clocks`
| Campo | Tipo | Descripción |
|---|---|---|
| id | INT AUTO_INCREMENT | ID único |
| ip_address | VARCHAR(45) UNIQUE | IP del reloj ZKTeco |
| name | VARCHAR(100) | Nombre o destino |
| location | VARCHAR(100) | Ubicación física |
| is_active | TINYINT(1) | 1=Activo, 0=Inactivo |
| last_updated | TIMESTAMP | Última sincronización exitosa |
| created_at | TIMESTAMP | Fecha de registro |

### Tabla `users`
| Campo | Tipo | Descripción |
|---|---|---|
| id | INT AUTO_INCREMENT | ID único |
| username | VARCHAR(50) UNIQUE | Nombre de usuario |
| password_hash | VARCHAR(255) | Contraseña hasheada con bcrypt |
| is_admin | TINYINT(1) | 1=Administrador, 0=Usuario |
| created_at | TIMESTAMP | Fecha de creación |
| last_login | TIMESTAMP NULL | Último inicio de sesión |

### Tabla `sync_logs`
| Campo | Tipo | Descripción |
|---|---|---|
| id | INT AUTO_INCREMENT | ID único |
| clock_id | INT | FK a clocks.id |
| status | ENUM('success','failed','error') | Estado de la sincronización |
| message | TEXT | Mensaje detallado |
| synced_at | TIMESTAMP | Fecha y hora del registro |

## Generar Usuario Administrador Manualmente

Si necesita generar un usuario administrador con otra contraseña:

```python
import bcrypt
password = "SuContraseña"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))
print(hashed.decode('utf-8'))
```

Luego inserte en la base de datos:

```sql
USE clock;
INSERT INTO users (username, password_hash, is_admin) 
VALUES ('nuevo_admin', 'HASH_GENERADO', TRUE);
```

O desde el contenedor MySQL:

```bash
docker exec -it zkteco-mysql mysql -u root -p clock
```

## Solución de Problemas

### No se puede conectar al reloj
- Verificar que el reloj esté encendido y en la misma red
- Verificar la dirección IP correcta
- Algunos relojes requieren puertos adicionales o configuraciones
- Comprobar firewall entre servidor y reloj

### Error de conexión a MySQL
```bash
docker logs zkteco-mysql
docker logs zkteco-app
```

### Reiniciar contenedores
```bash
docker-compose restart
```

### Detener y eliminar todo (incluyendo datos)
```bash
docker-compose down -v
```

> **Advertencia:** `-v` elimina el volumen de MySQL, borrando todos los datos.

### Verificar conectividad al reloj desde el contenedor
```bash
docker exec -it zkteco-app ping IP_DEL_RELOJ
```

## Notas Técnicas

- La librería `pyzk` se utiliza para comunicarse con los relojes ZKTeco por el puerto 4370 (UDP/TCP)
- Las contraseñas se almacenan con bcrypt (rounds=12)
- El timezone configurado es `America/Argentina/Buenos_Aires`
- MySQL 8.0 en contenedor separado con volumen persistente
- La aplicación Flask corre en modo producción (debug=False)

## Seguridad

- Cambie todas las contraseñas por defecto
- Use `APP_SECRET_KEY` único y aleatorio
- Restrinja el acceso a los puertos 8080 y 3306 solo a redes confiables
- En producción, considere usar HTTPS con un reverse proxy (nginx)
- Mantenga los contenedores actualizados

## Soporte

Para reportar problemas o sugerencias, revise los logs de sincronización en la interfaz web o en los contenedores.
# Clock_Update
