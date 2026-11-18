import logging

# Настройка базового логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"), # Запись в файл
        logging.StreamHandler()                          # Вывод в консоль
    ]
)

# Создаем переменную logger, которую ищет ваш код
logger = logging.getLogger(__name__)
