import os
import sys
import signal
import asyncio
import logging
from processing import monitor_ips_with_telegram_delay
from objects import add_new_object, update_existing_object, choose_object_name
from db_manager import initialize_db, execute_query, toggle_logging, is_logging_enabled

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="service.log"
)

LOCK_FILE = "/tmp/monitor_service.lock"


def is_service_running():
    """Проверяет, запущен ли сервис."""
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, "r") as f:
            pid = int(f.read().strip())
        if os.path.exists(f"/proc/{pid}"):
            return pid
    return None


def daemonize():
    """Создает демон-процесс."""
    if os.fork() > 0:
        sys.exit()

    os.setsid()

    if os.fork() > 0:
        sys.exit()

    sys.stdout.flush()
    sys.stderr.flush()

    with open("/dev/null", "r") as devnull:
        os.dup2(devnull.fileno(), sys.stdin.fileno())
    with open("/dev/null", "a") as devnull:
        os.dup2(devnull.fileno(), sys.stdout.fileno())
        os.dup2(devnull.fileno(), sys.stderr.fileno())


def start_service(object_name, object_data, delay):
    """Запуск сервиса мониторинга."""
    pid = is_service_running()
    if pid:
        print(f"Сервис уже запущен с PID {pid}.")
        return

    daemonize()

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

    logging.info(f"Сервис запущен для объекта '{object_name}' с PID {os.getpid()}.")
    try:
        asyncio.run(monitor_ips_with_telegram_delay(object_data, delay))
    except Exception as e:
        logging.error(f"Ошибка в сервисе: {e}")
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)


def stop_service():
    """Остановка запущенного сервиса."""
    pid = is_service_running()
    if pid:
        os.kill(pid, signal.SIGTERM)
        os.remove(LOCK_FILE)
        print(f"Сервис с PID {pid} остановлен.")
        logging.info(f"Сервис с PID {pid} остановлен.")
    else:
        print("Сервис не запущен.")


def choose_monitoring_object():
    """Выбор объекта для мониторинга и запуск сервиса."""
    object_name = choose_object_name()
    if not object_name:
        return

    delay = int(input("Введите задержку между проверками (в секундах, по умолчанию 10): ") or 10)
    query = "SELECT ip_list, telegram_token, telegram_chat_ids FROM objects WHERE object_name = ?"
    result = execute_query(query, (object_name,))
    if not result:
        print(f"Объект '{object_name}' не найден.")
        return

    ip_list, telegram_token, telegram_chat_ids = result[0]
    object_data = {
        "object_name": object_name,
        "ip_list": ip_list.split(","),
        "telegram_token": telegram_token,
        "telegram_chat_ids": telegram_chat_ids.split(","),
    }

    print("\nВыберите действие:")
    print("1. Запустить мониторинг вручную (нажмите Ctrl+C для остановки).")
    print("2. Запустить как сервис.")
    print("3. Включить/выключить логирование.")
    choice = input("Введите номер действия: ").strip()

    if choice == "1":
        print("Запуск мониторинга вручную...")
        try:
            asyncio.run(monitor_ips_with_telegram_delay(object_data, delay))
        except KeyboardInterrupt:
            print("\nМониторинг остановлен вручную.")
    elif choice == "2":
        start_service(object_name, object_data, delay)
    elif choice == "3":
        current_logging = is_logging_enabled(object_name)
        toggle_logging(object_name, enable=not current_logging)
        print(f"Логирование {'включено' if not current_logging else 'отключено'} для объекта '{object_name}'.")
    else:
        print("Некорректный выбор.")


def main_menu():
    """Главное меню программы."""
    while True:
        print("\nГлавное меню:")
        print("1. Добавить новый объект")
        print("2. Обновить существующий объект")
        print("3. Выбрать объект для мониторинга")
        print("4. Остановить сервис")
        print("5. Выход")
        choice = input("Введите номер действия: ").strip()

        if choice == "1":
            add_new_object()
        elif choice == "2":
            update_existing_object()
        elif choice == "3":
            choose_monitoring_object()
        elif choice == "4":
            stop_service()
        elif choice == "5":
            print("Выход из программы.")
            break
        else:
            print("Некорректный выбор. Попробуйте снова.")


if __name__ == "__main__":
    initialize_db()

    pid = is_service_running()
    if pid:
        print(f"Сервис уже запущен с PID {pid}.")
        choice = input("Вы хотите остановить текущий сервис? (y/n): ").strip().lower()
        if choice == "y":
            stop_service()
        else:
            print("Сервис остается запущенным.")
            sys.exit()
    else:
        main_menu()
