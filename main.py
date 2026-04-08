import requests
from lxml import html
import time
import os

# -----------------------------
# НАСТРОЙКИ
# -----------------------------

CHAT_ID = "1428398444"
BOT_TOKEN = "8752041379:AAFZmtXnsxA-x4-lRmL7xi2UsdE6GbDU_Ss"

BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
PHOTO_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

MSG_NO_FULL = (
    "🔥 <b>{}</b> теперь доступна в TestFlight!\n"
    "<a href='{}'>Открыть в TestFlight</a>"
)

MSG_FULL = "<b>{}</b> снова заполнена."

TESTFLIGHT_URL = "https://testflight.apple.com/join/{}"

# Новый, надёжный XPATH для иконки
XPATH_ICON = '//meta[@property="og:image"]/@content'
XPATH_TITLE = '//title/text()'
XPATH_STATUS = '//span[contains(text(), "beta") or contains(text(), "accepting") or contains(text(), "full") or contains(text(), "версии")]/text()'


# -----------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# -----------------------------

def safe_sleep(seconds):
    """Мягкий сон, чтобы Railway не считал процесс зависшим."""
    end = time.time() + seconds
    while time.time() < end:
        time.sleep(1)


def load_ids():
    """Загружает список ID из config.txt."""
    try:
        with open("config.txt", "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except:
        print("Файл config.txt не найден!")
        return []


def send_telegram_message(message, icon_url=None):
    """Отправка сообщения с иконкой (как файл)."""

    if icon_url:
        try:
            img_data = requests.get(icon_url, timeout=10).content
            files = {"photo": ("icon.png", img_data)}

            requests.post(
                PHOTO_URL,
                data={"chat_id": CHAT_ID, "caption": message, "parse_mode": "html"},
                files=files
            )
            return

        except Exception as e:
            print("Ошибка загрузки иконки:", e)

    # fallback — без картинки
    requests.get(
        BOT_URL,
        params={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "html",
            "disable_web_page_preview": "true"
        }
    )


# -----------------------------
# ОСНОВНАЯ ЛОГИКА МОНИТОРИНГА
# -----------------------------

def watch(notify_full=False):
    data = {}

    watch_ids = load_ids()
    last_config_time = os.path.getmtime("config.txt")

    print("[CONFIG] Initial watch list:", watch_ids)

    while True:

        # --- Проверяем, изменился ли config.txt ---
        try:
            new_time = os.path.getmtime("config.txt")
            if new_time != last_config_time:
                last_config_time = new_time
                watch_ids = load_ids()
                print("[CONFIG] Updated watch list:", watch_ids)
        except:
            pass

        # --- Основной цикл проверки ---
        for tf_id in watch_ids:

            try:
                req = requests.get(
                    TESTFLIGHT_URL.format(tf_id),
                    headers={
                        "Accept-Language": "en-us",
                        "User-Agent": "Mozilla/5.0"
                    },
                    timeout=10
                )
            except:
                safe_sleep(30)
                continue

            page = html.fromstring(req.text)

            status_list = page.xpath(XPATH_STATUS)
            if not status_list:
                continue

            status_text = status_list[0].strip()

            is_full = (
                "full" in status_text.lower() or
                "not accepting" in status_text.lower() or
                "укомплектован" in status_text.lower() or
                "недоступна" in status_text.lower() or
                "заверш" in status_text.lower()
            )

            free_slots = not is_full

            if tf_id not in data or data[tf_id] != free_slots:

                title_raw = page.xpath(XPATH_TITLE)
                if title_raw:
                    raw = title_raw[0].strip()
                    raw = raw.replace(" - TestFlight - Apple", "")
                    raw = raw.replace("Join the ", "")
                    raw = raw.replace(" beta", "")
                    title = raw if raw else "Unknown App"
                else:
                    title = "Unknown App"

                icon_raw = page.xpath(XPATH_ICON)
                icon_url = icon_raw[0] if icon_raw else None

                if free_slots:
                    message = MSG_NO_FULL.format(title, TESTFLIGHT_URL.format(tf_id))
                else:
                    if not notify_full:
                        data[tf_id] = free_slots
                        continue
                    message = MSG_FULL.format(title)

                send_telegram_message(message, icon_url)
                data[tf_id] = free_slots

            if free_slots:
                safe_sleep(180)
            else:
                safe_sleep(900)


# -----------------------------
# ЗАПУСК
# -----------------------------

watch()
