from telethon import TelegramClient
from common.memory_manager import MemoryManager


class ProcessVars(object):
    account: dict
    client: TelegramClient
    memory_manager: MemoryManager
    loop_tasks: dict = {}
