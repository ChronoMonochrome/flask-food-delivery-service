# bot/logger.py
import logging
import functools
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

#from app import app

# --- MODIFIED LOG FORMAT ---
# We'll make the 'source' part optional or use 'name' for SQLAlchemy
# A flexible approach:
class CustomFormatter(logging.Formatter):
    def format(self, record):
        # Default behavior: use the source if available, otherwise use the logger name
        # If 'source' is in record.__dict__, it's likely from our CustomLogger
        # Otherwise, use the standard 'name' for loggers like 'sqlalchemy.engine'
        record.display_source = record.source if hasattr(record, 'source') else record.name
        return super().format(record)

# The log format now references 'display_source'
log_format = "[%(asctime)s] %(levelname)s %(display_source)s: %(message)s"


# Настройка директории для логов
logs_directory = "/app/logs"
if not os.path.exists(logs_directory):
    os.makedirs(logs_directory, exist_ok=True)

class CustomLogger:
    def __init__(self, source: str, log_to_file: bool = True, log_to_console: bool = True, base_dir: str = "./logs", log_rotate_days = 30):
        self.source = source
        self.logger = logging.getLogger(source)
        self.logger.setLevel(logging.INFO)

        # Clear existing handlers to prevent duplicate logs if re-initializing
        if self.logger.handlers:
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)
                try:
                    handler.close()
                except Exception as e:
                    print(f"Error closing handler during init cleanup for {source}: {e}")

        self.log_directory = base_dir
        if not os.path.exists(self.log_directory):
            os.makedirs(self.log_directory)

        # --- Use CustomFormatter here ---
        self.formatter = CustomFormatter(log_format)

        if log_to_file:
            self._setup_file_handler(log_rotate_days)
        self._setup_console_handlers(log_to_console, self.logger.level)

    def destroy(self):
        for handler in self.logger.handlers[:]:
            try:
                handler.close()
                self.logger.removeHandler(handler)
            except Exception as e:
                print(f"Error closing handler for {self.source} logger: {e}")

    def _setup_file_handler(self, log_rotate_days: int):
        log_file_path = os.path.join(self.log_directory, f"{self.source.replace('.', '_')}.log") # Sanitize source for filename
        file_handler = TimedRotatingFileHandler(
            log_file_path,
            when="midnight",
            interval=log_rotate_days,
            backupCount=5,
            encoding='utf-8',
            delay=True
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(self.formatter)

        def rename_rotated_logs(prefix):
            def namer(default_name):
                base_name_with_date, ext = os.path.splitext(default_name)
                base_file_name_part = os.path.basename(base_name_with_date)

                parts = base_file_name_part.rsplit('.', 1)
                if len(parts) > 1 and parts[-1].count('-') == 2:
                    date_suffix = parts[-1]
                    original_file_name_prefix = parts[0]
                    # Ensure the prefix is correctly derived for renaming
                    source_part = prefix.replace('.', '_')
                    new_filename = f"{source_part}_{date_suffix.replace('-', '_')}.log"
                else:
                    new_filename = f"{prefix.replace('.', '_')}_{datetime.now().strftime('%Y_%m_%d')}.log"

                return os.path.join(self.log_directory, new_filename)
            return namer

        file_handler.namer = rename_rotated_logs(self.source)

        original_do_rollover = file_handler.doRollover
        def custom_do_rollover():
            if file_handler.stream:
                try:
                    file_handler.stream.close()
                except Exception as e:
                    print(f"Error closing log file stream during rollover for {self.source}: {e}")
            original_do_rollover()

        file_handler.doRollover = custom_do_rollover
        self.logger.addHandler(file_handler)

    def _setup_console_handlers(self, log_to_console: bool, logger_level: int):
        error_console_handler = logging.StreamHandler()
        error_console_handler.setLevel(logging.ERROR)
        error_console_handler.setFormatter(self.formatter)
        self.logger.addHandler(error_console_handler)

        if log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logger_level)
            console_handler.setFormatter(self.formatter)
            self.logger.addHandler(console_handler)

    def _log(self, level: int, message: str, exc_info=None):
        # We still add 'source' here for our CustomLogger's own calls
        # The CustomFormatter will then decide whether to use 'source' or 'name'
        self.logger.log(level, message, extra={"source": self.source}, exc_info=exc_info)

    def info(self, message: str):
        self._log(logging.INFO, message)

    def error(self, message: str, exc_info=False):
        self._log(logging.ERROR, message, exc_info=exc_info)

    def warning(self, message: str):
        self._log(logging.WARNING, message)

    def debug(self, message: str):
        self._log(logging.DEBUG, message)

    def critical(self, message: str):
        self._log(logging.CRITICAL, message)

# --- Global logger instance creation (now correctly placed) ---
logger = CustomLogger(source="bot.main", log_to_file=True, log_to_console=True)

# --- Configure SQLAlchemy logging to use your CustomLogger's file handler ---
sqlalchemy_logger = logging.getLogger('sqlalchemy.engine.Engine')
# Set level to INFO or DEBUG based on Config.DEBUG
sqlalchemy_logger.setLevel(logging.INFO if not True else logging.DEBUG)

# Add the file handler from your main logger instance to the SQLAlchemy logger.
# This ensures SQLAlchemy logs go to the same file.
for handler in logger.logger.handlers:
    if isinstance(handler, TimedRotatingFileHandler):
        sqlalchemy_logger.addHandler(handler)

# IMPORTANT: Prevent SQLAlchemy logs from propagating to the root logger if the root logger
# has a console handler and you only want SQLAlchemy logs in the file.
sqlalchemy_logger.propagate = False


def error_handler(func):
    """
    Decorator to catch exceptions in async functions and log them.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
    return wrapper

