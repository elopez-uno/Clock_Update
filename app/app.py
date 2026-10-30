import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pymysql
import bcrypt
from datetime import datetime, date, timedelta
from zk import ZK
import functools

app = Flask(__name__)
app.secret_key = os.getenv('APP_SECRET_KEY', 'change-me')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicie sesión para acceder.'

def get_db_connection():
    try:
        connection = pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'mysql-db'),
            user=os.getenv('MYSQL_USER', 'clock_user'),
            password=os.getenv('MYSQL_PASSWORD', 'clock_password'),
            database=os.getenv('MYSQL_DATABASE', 'clock'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

class User(UserMixin):
    def __init__(self, id, username, is_admin):
        self.id = id
        self.username = username
        self.is_admin = bool(is_admin)

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()
        conn.close()
        if user_data:
            return User(user_data['id'], user_data['username'], user_data['is_admin'])
    except:
        pass
    return None

def admin_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Acceso denegado. Se requieren permisos de administrador.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        if not conn:
            flash('Error de conexión a la base de datos', 'danger')
            return render_template('login.html')
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                user_data = cursor.fetchone()
            
            if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data['password_hash'].encode('utf-8')):
                user = User(user_data['id'], user_data['username'], user_data['is_admin'])
                login_user(user)
                cursor.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user_data['id'],))
                conn.commit()
                flash('Inicio de sesión exitoso', 'success')
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('index'))
            else:
                flash('Usuario o contraseña incorrectos', 'danger')
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        finally:
            conn.close()
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    conn = get_db_connection()
    clocks = []
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM clocks ORDER BY name")
                clocks = cursor.fetchall()
        finally:
            conn.close()
    return render_template('index.html', clocks=clocks)

@app.route('/clocks')
@login_required
@admin_required
def clocks_list():
    conn = get_db_connection()
    clocks = []
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM clocks ORDER BY name")
                clocks = cursor.fetchall()
        finally:
            conn.close()
    return render_template('clocks.html', clocks=clocks)

@app.route('/clocks/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_clock():
    if request.method == 'POST':
        ip_address = request.form.get('ip_address')
        name = request.form.get('name')
        location = request.form.get('location', '')
        is_active = 1 if request.form.get('is_active') else 0
        
        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO clocks (ip_address, name, location, is_active) VALUES (%s, %s, %s, %s)",
                        (ip_address, name, location, is_active)
                    )
                conn.commit()
                flash('Reloj agregado correctamente', 'success')
                return redirect(url_for('clocks_list'))
            except pymysql.err.IntegrityError:
                flash('Ya existe un reloj con esa dirección IP', 'danger')
            except Exception as e:
                flash(f'Error: {e}', 'danger')
            finally:
                conn.close()
    
    return render_template('add_clock.html')

@app.route('/clocks/edit/<int:clock_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_clock(clock_id):
    conn = get_db_connection()
    clock = None
    
    if conn:
        try:
            with conn.cursor() as cursor:
                if request.method == 'POST':
                    ip_address = request.form.get('ip_address')
                    name = request.form.get('name')
                    location = request.form.get('location', '')
                    is_active = 1 if request.form.get('is_active') else 0
                    
                    cursor.execute(
                        "UPDATE clocks SET ip_address=%s, name=%s, location=%s, is_active=%s WHERE id=%s",
                        (ip_address, name, location, is_active, clock_id)
                    )
                    conn.commit()
                    flash('Reloj actualizado correctamente', 'success')
                    return redirect(url_for('clocks_list'))
                else:
                    cursor.execute("SELECT * FROM clocks WHERE id = %s", (clock_id,))
                    clock = cursor.fetchone()
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        finally:
            conn.close()
    
    if not clock:
        flash('Reloj no encontrado', 'danger')
        return redirect(url_for('clocks_list'))
    
    return render_template('edit_clock.html', clock=clock)

@app.route('/clocks/delete/<int:clock_id>')
@login_required
@admin_required
def delete_clock(clock_id):
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM clocks WHERE id = %s", (clock_id,))
            conn.commit()
            flash('Reloj eliminado correctamente', 'success')
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        finally:
            conn.close()
    return redirect(url_for('clocks_list'))

@app.route('/sync/<int:clock_id>')
@login_required
@admin_required
def sync_clock(clock_id):
    from scripts.sync_clocks import sync_single_clock
    result = sync_single_clock(clock_id)
    if result['success']:
        flash(f"Sincronización exitosa: {result['message']}", 'success')
    else:
        flash(f"Error en sincronización: {result['message']}", 'danger')
    return redirect(url_for('index'))

@app.route('/logs')
@login_required
@admin_required
def logs():
    conn = get_db_connection()
    logs = []
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT l.*, c.name as clock_name, c.ip_address 
                    FROM sync_logs l 
                    LEFT JOIN clocks c ON l.clock_id = c.id 
                    ORDER BY l.synced_at DESC 
                    LIMIT 100
                """)
                logs = cursor.fetchall()
        finally:
            conn.close()
    return render_template('logs.html', logs=logs)

@app.route('/users')
@login_required
@admin_required
def users_list():
    conn = get_db_connection()
    users = []
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, username, is_admin, created_at, last_login FROM users ORDER BY username")
                users = cursor.fetchall()
        finally:
            conn.close()
    return render_template('users.html', users=users)

@app.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        is_admin = 1 if request.form.get('is_admin') else 0
        
        conn = get_db_connection()
        if conn:
            try:
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO users (username, password_hash, is_admin) VALUES (%s, %s, %s)",
                        (username, password_hash, is_admin)
                    )
                conn.commit()
                flash('Usuario agregado correctamente', 'success')
                return redirect(url_for('users_list'))
            except pymysql.err.IntegrityError:
                flash('El nombre de usuario ya existe', 'danger')
            except Exception as e:
                flash(f'Error: {e}', 'danger')
            finally:
                conn.close()
    
    return render_template('add_user.html')


@app.route('/clocks/<int:clock_id>/users')
@login_required
@admin_required
def clock_users(clock_id):
    conn = get_db_connection()
    clock = None
    users_list = []
    error = None
    
    if not conn:
        flash('Error de conexión a la base de datos', 'danger')
        return redirect(url_for('index'))
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM clocks WHERE id = %s", (clock_id,))
            clock = cursor.fetchone()
    finally:
        conn.close()
    
    if not clock:
        flash('Reloj no encontrado', 'danger')
        return redirect(url_for('index'))
    
    if not clock['is_active']:
        flash('El reloj está marcado como inactivo. Actívalo para consultar sus datos.', 'warning')
        return redirect(url_for('index'))
    
    ip = clock['ip_address']
    port = 4370
    zk = ZK(ip, port=port, timeout=30)
    
    try:
        conn_zk = zk.connect()
        if not conn_zk:
            error = f'No se pudo conectar al reloj {ip}. Verificá red/encendido.'
        else:
            try:
                users = conn_zk.get_users()
                for u in users:
                    users_list.append({
                        'uid': getattr(u, 'uid', ''),
                        'user_id': getattr(u, 'user_id', ''),
                        'name': getattr(u, 'name', ''),
                        'privilege': getattr(u, 'privilege', 0),
                        'password': getattr(u, 'password', ''),
                        'group_id': getattr(u, 'group_id', ''),
                        'card': getattr(u, 'card', '')
                    })
                users_list.sort(key=lambda x: str(x['user_id']))
            except Exception as e:
                error = f'Error al obtener usuarios: {e}'
            finally:
                try:
                    conn_zk.disconnect()
                except:
                    pass
    except Exception as e:
        error = f'Error: {e}'
    
    return render_template('clock_users.html', clock=clock, users=users_list, error=error)


@app.route('/clocks/<int:clock_id>/attendance', methods=['GET', 'POST'])
@login_required
@admin_required
def clock_attendance(clock_id):
    conn = get_db_connection()
    clock = None
    attendance_list = []
    error = None
    
    if request.method == 'POST':
        start_str = request.form.get('start_date')
        end_str = request.form.get('end_date')
    else:
        end_str = date.today().strftime('%Y-%m-%d')
        start_str = (date.today() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    if not conn:
        flash('Error de conexión a la base de datos', 'danger')
        return redirect(url_for('index'))
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM clocks WHERE id = %s", (clock_id,))
            clock = cursor.fetchone()
    finally:
        conn.close()
    
    if not clock:
        flash('Reloj no encontrado', 'danger')
        return redirect(url_for('index'))
    
    if not clock['is_active']:
        flash('El reloj está marcado como inactivo. Actívalo para consultar sus datos.', 'warning')
        return redirect(url_for('index'))
    
    ip = clock['ip_address']
    port = 4370
    zk = ZK(ip, port=port, timeout=30)
    
    try:
        start_dt = datetime.strptime(start_str, '%Y-%m-%d')
        end_dt = datetime.strptime(end_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    except ValueError:
        error = 'Fechas inválidas. Usá formato AAAA-MM-DD'
        return render_template('clock_attendance.html', clock=clock, attendance=[], error=error, start_date=start_str, end_date=end_str)
    
    try:
        conn_zk = zk.connect()
        if not conn_zk:
            error = f'No se pudo conectar al reloj {ip}. Verificá red/encendido.'
        else:
            try:
                records = conn_zk.get_attendance()
                if records:
                    for r in records:
                        punch_time = getattr(r, 'timestamp', None)
                        if not punch_time:
                            continue
                        if punch_time < start_dt or punch_time > end_dt:
                            continue
                        attendance_list.append({
                            'user_id': getattr(r, 'user_id', ''),
                            'uid': getattr(r, 'uid', ''),
                            'timestamp': punch_time,
                            'status': getattr(r, 'status', ''),
                            'punch': getattr(r, 'punch', ''),
                            'verify_mode': getattr(r, 'verify_mode', '')
                        })
                    attendance_list.sort(key=lambda x: x['timestamp'], reverse=True)
                else:
                    error = 'No se encontraron marcaciones en the reloj.'
            except Exception as e:
                error = f'Error al obtener marcaciones: {e}'
            finally:
                try:
                    conn_zk.disconnect()
                except:
                    pass
    except Exception as e:
        error = f'Error: {e}'
    
    return render_template('clock_attendance.html', clock=clock, attendance=attendance_list, error=error, start_date=start_str, end_date=end_str)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
