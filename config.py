import os
import sys
import configparser
from loguru import logger

TEMP_PATH = os.path.join(os.getcwd(), 'tmp')
LOG_PATH = os.path.join(TEMP_PATH, 'debug.log')
COOKIE_PATH = os.path.join(TEMP_PATH, 'cookie.json')

if not os.path.exists(TEMP_PATH):
    os.makedirs(TEMP_PATH)

logger.remove()
console_format = "{time:HH:mm:ss} | {level} | {message}"
file_format = "{time:HH:mm:ss} | {level} | {function}:{line} - {message}"

logger.add(sys.stdout, format=console_format, level="INFO", colorize=True)
logger.add(LOG_PATH, format=file_format, level="DEBUG")

config = configparser.ConfigParser()
config.read('config.cfg', encoding='utf-8')
