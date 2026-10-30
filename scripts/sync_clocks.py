#!/usr/bin/env python3
import os
import sys
from datetime import datetime
import pymysql
from zk import ZK
import pytz

# Add parent directory to path
sys.path.append('/app')

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

def log_sync(clock_id, status, message):
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO sync_logs (clock_id, status, message) VALUES (%s, %s, %s)",
                    (clock_id, status, message)
                )
            conn.commit()
        except Exception as e:
            print(f"Error logging sync: {e}")
        finally:
            conn.close()

def sync_single_clock(clock_id):
    conn = get_db_connection()
    if not conn:
        return {'success': False, 'message': 'No database connection'}
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM clocks WHERE id = %s", (clock_id,))
            clock = cursor.fetchone()
        
        if not clock:
            conn.close()
            return {'success': False, 'message': 'Clock not found'}
        
        if not clock['is_active']:
            conn.close()
            log_sync(clock_id, 'failed', 'Clock is inactive')
            return {'success': False, 'message': 'Clock is inactive'}
        
        ip = clock['ip_address']
        port = 4370
        zk = ZK(ip, port=port, timeout=30)
        
        try:
            conn_zk = zk.connect()
            if not conn_zk:
                log_sync(clock_id, 'failed', f'Cannot connect to {ip}')
                conn.close()
                return {'success': False, 'message': f'Cannot connect to {ip}'}
            
            # Set device time to server time
            now = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
            conn_zk.set_time(now)
            
            # Update last_updated
            with conn.cursor() as cursor:
                cursor.execute("UPDATE clocks SET last_updated = NOW() WHERE id = %s", (clock_id,))
            conn.commit()
            
            conn_zk.disconnect()
            log_sync(clock_id, 'success', f'Time synchronized at {now.strftime("%Y-%m-%d %H:%M:%S")}')
            conn.close()
            return {'success': True, 'message': f'Time updated successfully'}
            
        except Exception as e:
            log_sync(clock_id, 'error', str(e))
            conn.close()
            return {'success': False, 'message': str(e)}
            
    except Exception as e:
        if conn:
            conn.close()
        return {'success': False, 'message': str(e)}

def sync_all_clocks():
    conn = get_db_connection()
    if not conn:
        print("No database connection")
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM clocks WHERE is_active = 1")
            clocks = cursor.fetchall()
        
        print(f"[{datetime.now()}] Starting sync for {len(clocks)} active clocks")
        for clock in clocks:
            result = sync_single_clock(clock['id'])
            print(f"  Clock {clock['id']}: {result['message']}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    sync_all_clocks()
