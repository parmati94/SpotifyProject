import logging
import os
from logging.handlers import TimedRotatingFileHandler
import datetime

class CustomTimedRotatingFileHandler(TimedRotatingFileHandler):
    def doRollover(self):
        self.baseFilename = os.path.join(log_dir, f"logfile_{datetime.datetime.now().strftime('%Y-%m-%d')}.log")
        TimedRotatingFileHandler.doRollover(self)

log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
numeric_level = getattr(logging, log_level, None)

if not isinstance(numeric_level, int):
    raise ValueError(f'Invalid log level: {log_level}')

log_format = '%(asctime)s [%(levelname)s] %(filename)s: %(message)s'

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Join it with 'logs' to get the path to the logs directory
log_dir = os.path.join(script_dir, 'logs')

if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Create a timed rotating file handler that creates a new file every day and keeps logs for a week
# The log files are named with the current date
file_handler = CustomTimedRotatingFileHandler(os.path.join(log_dir, f"logfile_{datetime.datetime.now().strftime('%Y-%m-%d')}.log"), when='midnight', interval=1, backupCount=7)
file_handler.setLevel(numeric_level)

# Create a console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(numeric_level)

# Create a formatter and set it for both handlers
formatter = logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Get the root logger and set its level
logger = logging.getLogger()
logger.setLevel(numeric_level)

print(f"Log level set to: {logging.getLevelName(logger.level)}")

# Add both handlers to the root logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)