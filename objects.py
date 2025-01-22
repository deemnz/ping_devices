import ipaddress
import logging
from db_manager import save_object_config, execute_query, update_object_delay, toggle_logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_ip_range(ip_input):
    """Парсинг диапазона IP."""
    try:
        if '-' in ip_input:
            start_ip, end_ip = ip_input.split('-')
            start_ip = ipaddress.IPv4Address(start_ip.strip())
            end_ip = ipaddress.IPv4Address(end_ip.strip())
            return [str(ipaddress.IPv4Address(ip)) for ip in range(int(start_ip), int(end_ip) + 1)]
        else:
            ipaddress.IPv4Address(ip_input)  # Проверка корректности
            return [ip_input.strip()]
    except ValueError:
        raise ValueError(f"Некорректный ввод IP или диапазона: {ip_input}")

def get_all_objects():
    """Получение списка всех объектов."""
    query = "SELECT object_name FROM objects"
    results = execute_query(query)
    return [row[0] for row in results] if results else []

def choose_object_name():
    """Выбор имени объекта из списка."""
    object_names = get_all_objects()
    if not object_names:
        print("Объекты отсутствуют в базе данных.")
        return None

    print("Доступные объекты:")
    for idx, name in enumerate(object_names, start=1):
        print(f"{idx}. {name}")

    try:
        choice = int(input("Выберите объект (по номеру): ").strip())
        if 1 <= choice <= len(object_names):
            return object_names[choice - 1]
        else:
            print("Некорректный выбор.")
            return None
    except ValueError:
        print("Некорректный ввод.")
        return None

def add_new_object():
    """Добавление нового объекта."""
    object_name = input("Введите имя объекта: ").strip()
    if not object_name:
        print("Имя объекта не может быть пустым.")
        return

    print("Введите IP-адреса или диапазоны (формат: start-end). Для завершения ввода оставьте строку пустой.")
    ip_list = []
    while True:
        ip_input = input("IP или диапазон: ").strip()
        if not ip_input:
            break
        try:
            ip_list.extend(parse_ip_range(ip_input))
        except ValueError as e:
            print(e)

    if not ip_list:
        print("Список IP-адресов не может быть пустым.")
        return

    telegram_token = input("Введите Telegram-токен: ").strip()
    if not telegram_token:
        print("Telegram-токен не может быть пустым.")
        return

    telegram_chat_ids = input("Введите Telegram Chat IDs (через запятую): ").strip().split(",")
    if not telegram_chat_ids:
        print("Telegram Chat IDs не могут быть пустыми.")
        return

    delay = int(input("Введите задержку в секундах (по умолчанию 10): ").strip() or 10)
    save_object_config(object_name, ip_list, telegram_token, telegram_chat_ids, delay)

    for ip in ip_list:
        existing_name_query = "SELECT ip_name FROM ip_names WHERE ip_address = ? AND object_name = ?"
        existing_name = execute_query(existing_name_query, (ip, object_name))
        existing_name = existing_name[0][0] if existing_name else ""
        ip_name = input(f"Введите имя для IP {ip} (текущий: {existing_name if existing_name else 'не задан'}): ").strip() or existing_name
        query = "INSERT OR REPLACE INTO ip_names (ip_address, object_name, ip_name) VALUES (?, ?, ?)"
        execute_query(query, (ip, object_name, ip_name))

    logging.info(f"Объект '{object_name}' успешно добавлен.")
    print(f"Объект '{object_name}' успешно добавлен.")

def update_existing_object():
    """Обновление данных существующего объекта."""
    object_name = choose_object_name()
    if not object_name:
        return

    print("Введите новые данные. Чтобы оставить текущие значения, нажмите Enter.")
    query = "SELECT ip_list, telegram_token, telegram_chat_ids, delay FROM objects WHERE object_name = ?"
    current_data = execute_query(query, (object_name,))

    if not current_data:
        print(f"Объект '{object_name}' не найден.")
        return

    current_ip_list, current_token, current_chat_ids, current_delay = current_data[0]
    print(f"Текущие данные:\nIP-адреса: {current_ip_list}\nTelegram Token: {current_token}\nChat IDs: {current_chat_ids}\nЗадержка: {current_delay}")

    new_ip_list = input("Введите новые IP-адреса или диапазоны (через запятую): ").strip()
    if new_ip_list:
        parsed_ips = []
        for ip_input in new_ip_list.split(","):
            try:
                parsed_ips.extend(parse_ip_range(ip_input.strip()))
            except ValueError as e:
                print(e)
        new_ip_list = parsed_ips
    else:
        new_ip_list = current_ip_list.split(",")

    telegram_token = input("Введите новый Telegram-токен: ").strip() or current_token
    telegram_chat_ids = input("Введите новые Chat IDs (через запятую): ").strip() or current_chat_ids
    delay = input("Введите новую задержку (в секундах): ").strip() or current_delay

    save_object_config(object_name, new_ip_list, telegram_token, telegram_chat_ids.split(","), int(delay))

    for ip in new_ip_list:
        ip_name_query = "SELECT ip_name FROM ip_names WHERE ip_address = ? AND object_name = ?"
        existing_name = execute_query(ip_name_query, (ip, object_name))
        existing_name = existing_name[0][0] if existing_name else ip
        ip_name = input(f"Введите имя для IP {ip} (текущий: {existing_name}): ").strip() or existing_name
        query = "INSERT OR REPLACE INTO ip_names (ip_address, object_name, ip_name) VALUES (?, ?, ?)"
        execute_query(query, (ip, object_name, ip_name))

    print(f"Данные объекта '{object_name}' успешно обновлены.")
