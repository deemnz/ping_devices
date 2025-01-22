### db_manager.py
import sqlite3
import logging
from datetime import datetime

DB_NAME = "config.db"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def ensure_column_exists(table_name, column_name, column_definition):
    """
    Проверяет наличие колонки и добавляет ее, если она отсутствует.
    """
    try:
        query = f"PRAGMA table_info({table_name})"
        columns = execute_query(query)
        column_names = [col[1] for col in columns]
        if column_name not in column_names:
            alter_query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
            execute_query(alter_query)
            logging.info(f"Добавлена колонка '{column_name}' в таблицу '{table_name}'.")
    except Exception as e:
        logging.error(f"Ошибка при добавлении колонки '{column_name}' в таблицу '{table_name}': {e}")


def initialize_db():
    ensure_column_exists("ip_names", "connection_status", "TEXT DEFAULT NULL")
    """Инициализация базы данных."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("""
        CREATE TABLE IF NOT EXISTS objects (
            object_name TEXT PRIMARY KEY,
            ip_list TEXT,
            telegram_token TEXT,
            telegram_chat_ids TEXT,
            delay INTEGER DEFAULT 10,
            connection_status INTEGER DEFAULT NULL,
            extended_logging INTEGER DEFAULT 0
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS ip_names (
            ip_address TEXT,
            object_name TEXT,
            ip_name TEXT,
            PRIMARY KEY (ip_address, object_name)
        )
        """)
        logging.info("База данных успешно инициализирована.")
    except sqlite3.Error as e:
        logging.error(f"Ошибка при создании базы данных: {e}")
    finally:
        conn.commit()
        conn.close()

def execute_query(query, params=None):
    """Выполнение запроса к базе данных."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        if params:
            c.execute(query, params)
        else:
            c.execute(query)
        conn.commit()
        return c.fetchall()
    except sqlite3.Error as e:
        logging.error(f"Ошибка выполнения запроса: {e}")
        return None
    finally:
        conn.close()

def save_object_config(object_name, ip_list, telegram_token, telegram_chat_ids, delay):
    """Сохранение или обновление конфигурации объекта."""
    ip_list_str = ",".join(ip_list)
    telegram_chat_ids_str = ",".join(telegram_chat_ids)
    query = """
    INSERT OR REPLACE INTO objects (object_name, ip_list, telegram_token, telegram_chat_ids, delay)
    VALUES (?, ?, ?, ?, ?)
    """
    execute_query(query, (object_name, ip_list_str, telegram_token, telegram_chat_ids_str, delay))

def update_object_delay(object_name, new_delay):
    """Обновление времени задержки."""
    query = "UPDATE objects SET delay = ? WHERE object_name = ?"
    execute_query(query, (new_delay, object_name))

def is_logging_enabled(object_name):
    """Проверка состояния расширенного логирования."""
    query = "SELECT extended_logging FROM objects WHERE object_name = ?"
    result = execute_query(query, (object_name,))
    return result and result[0][0] == 1

def toggle_logging(object_name, enable):
    """Включение или отключение логирования."""
    query = "UPDATE objects SET extended_logging = ? WHERE object_name = ?"
    execute_query(query, (1 if enable else 0, object_name))


def save_ip_name(ip_address, object_name, ip_name):
    """Сохранение или обновление имени IP."""
    query = "INSERT OR REPLACE INTO ip_names (ip_address, object_name, ip_name) VALUES (?, ?, ?)"
    execute_query(query, (ip_address, object_name, ip_name))
    logging.info(f"Имя для IP {ip_address} ({object_name}) обновлено/добавлено как '{ip_name}'.")
