import asyncio
import logging
import signal
import os
from datetime import datetime, timedelta, timezone
from pythonping import ping
from db_manager import execute_query
from telegram.ext import ApplicationBuilder

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("service.log"),  # Логи сохраняются в файл
        logging.StreamHandler()
    ]
)

# Глобальная переменная для отслеживания работы сервиса
service_running = True

def reset_ip_statuses(object_name):
    """Сбрасывает статусы всех IP-адресов в базе данных для заданного объекта."""
    try:
        query = "UPDATE ip_names SET connection_status = NULL WHERE object_name = ?"
        execute_query(query, (object_name,))
        logging.info("Все статусы IP-адресов для объекта '%s' сброшены в базе данных.", object_name)
    except Exception as e:
        logging.error(f"Ошибка сброса статусов IP-адресов: {e}")

def get_ip_name(ip, object_name):
    """Получение имени IP из базы данных."""
    query = "SELECT ip_name FROM ip_names WHERE ip_address = ? AND object_name = ?"
    try:
        result = execute_query(query, (ip, object_name))
        if result:
            return result[0][0]
        else:
            logging.warning(f"Имя для IP {ip} не найдено в базе. Используется IP как имя.")
            return ip
    except Exception as e:
        logging.error(f"Ошибка выполнения запроса: {e}")
        return ip

async def send_telegram_message(token, chat_ids, message):
    """Отправка сообщения в Telegram."""
    app = ApplicationBuilder().token(token).build()
    for chat_id in chat_ids:
        try:
            await app.bot.send_message(chat_id=chat_id, text=message)
        except Exception as e:
            logging.error(f"Ошибка при отправке сообщения в Telegram для {chat_id}: {e}")

async def monitor_ips_with_telegram_delay(object_data, delay):
    """Мониторинг IP-адресов с подтверждением изменения статуса перед отправкой сообщения."""
    object_name = object_data.get("object_name")
    ip_addresses = object_data.get("ip_list")
    telegram_token = object_data.get("telegram_token")
    telegram_chat_ids = object_data.get("telegram_chat_ids")

    if not all([object_name, ip_addresses, telegram_token, telegram_chat_ids]):
        logging.error("Недостаточно данных для мониторинга.")
        return

    # Сброс статусов при первом запуске
    reset_ip_statuses(object_name)

    ip_status_cache = {}

    for ip in ip_addresses:
        # Инициализация статусов из базы данных
        try:
            query = "SELECT connection_status FROM ip_names WHERE ip_address = ? AND object_name = ?"
            result = execute_query(query, (ip, object_name))
            if result and result[0][0] is not None:
                ip_status_cache[ip] = result[0][0] == "доступен"
            else:
                ip_status_cache[ip] = None
        except Exception as e:
            logging.error(f"Ошибка при инициализации статуса IP {ip}: {e}")

    while service_running:
        for ip in ip_addresses:
            try:
                # Пинг IP с обработкой исключений
                try:
                    ping_response = ping(ip, count=1, timeout=1)
                    is_reachable = all(resp.success for resp in ping_response)
                    logging.info(f"Результат пинга IP {ip}: {ping_response}")
                except Exception as ping_error:
                    is_reachable = False
                    logging.error(f"Ошибка пинга IP {ip}: {ping_error}")

                ip_name = get_ip_name(ip, object_name)

                if ip_status_cache[ip] is None:
                    # Инициализация начального статуса
                    ip_status_cache[ip] = is_reachable
                    status = "доступен" if is_reachable else "недоступен"
                    query_update = "UPDATE ip_names SET connection_status = ? WHERE ip_address = ? AND object_name = ?"
                    execute_query(query_update, (status, ip, object_name))
                    logging.info(f"Инициализация статуса IP {ip_name} ({ip}): {status}.")
                elif ip_status_cache[ip] != is_reachable:
                    logging.info(f"Обнаружено изменение статуса IP {ip_name} ({ip}). Проверка стабильности...")

                    # Проверка стабильности нового статуса
                    stable_status = True
                    for second in range(delay):
                        await asyncio.sleep(1)
                        try:
                            recheck_response = ping(ip, count=1, timeout=1)
                            recheck_status = all(resp.success for resp in recheck_response)
                            logging.info(f"Проверка стабильности IP {ip} на {second + 1}-й секунде: {recheck_response}")
                        except Exception as recheck_error:
                            recheck_status = False
                            logging.error(f"Ошибка повторного пинга IP {ip}: {recheck_error}")

                        if recheck_status != is_reachable:
                            stable_status = False
                            logging.info(f"Статус IP {ip_name} ({ip}) вернулся к предыдущему. Прерываем проверку на {second + 1} секунде.")
                            break

                    if stable_status:
                        # Обновление статуса и отправка сообщения
                        ip_status_cache[ip] = is_reachable
                        status = "доступен" if is_reachable else "недоступен"
                        query_update = "UPDATE ip_names SET connection_status = ? WHERE ip_address = ? AND object_name = ?"
                        execute_query(query_update, (status, ip, object_name))

                        current_time = (datetime.now(timezone.utc) + timedelta(hours=2)).strftime("%d.%m.%Y %H:%M:%S")

                        message = (
                            f"{ip_name}: [ {ip} ]\n"
                            f"Дата: [ {current_time} ]\n"
                            f"Объект: [ {object_name} ]\n"
                            f"Статус: {'соединение восстановлено! ✅' if is_reachable else 'нет соединения! ⛔'}"
                        )
                        await send_telegram_message(telegram_token, telegram_chat_ids, message)
                        logging.info(f"Изменение статуса IP {ip_name} ({ip}) подтверждено и сообщение отправлено.")
                else:
                    logging.info(f"Статус IP {ip_name} ({ip}) не изменился. Текущий статус: {'доступен' if is_reachable else 'недоступен'}.")
            except Exception as e:
                logging.error(f"Ошибка при обработке IP {ip}: {e}")

        logging.info(f"Завершен цикл проверки для объекта '{object_name}'. Ожидание {delay} секунд.")
        await asyncio.sleep(delay)

# Обработка сигналов

def stop_service(signal_received, frame):
    global service_running
    service_running = False
    logging.info("Получен сигнал завершения. Сервис продолжит работать в фоне. Логи записываются в файл service.log.")

signal.signal(signal.SIGQUIT, stop_service)  # Ctrl + Q для выхода из сервиса без остановки работы
signal.signal(signal.SIGINT, lambda sig, frame: os._exit(0))  # Ctrl + C для завершения работы программы
