import asyncio
import traceback
import logging


logging.basicConfig(
    format='%(asctime)s %(name)s: [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)


class LoggerFilter(logging.Filter):
    def filter(self, record):
        if record.levelname not in ['ERROR', 'WARNING']:
            return True

        level_name = record.levelname
        logger_name = record.name
        log_message = record.getMessage()
        trace = traceback.format_exc()

        asyncio.run(send_alert_to_telegram_chat(
            level_name=level_name,
            logger_name=logger_name,
            log_message=log_message,
            args=None,
            err_message=trace
        ))

        return True


def get_logger(name):
    logger = logging.getLogger(name)
    logger.addFilter(LoggerFilter())

    return logger


async def send_alert_to_telegram_chat(
        level_name: str = None,
        logger_name: str = None,
        log_message: str = None,
        args: dict = None,
        err_message: str = '',
        short_error: str = None,
):
    # TODO: logging to telegram channel
    pass
