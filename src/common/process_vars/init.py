from common.memory_manager import MemoryManager
from common.process_vars.instance import process_vars


async def init_process_vars(logger):
    process_vars.memory_manager = MemoryManager(account=process_vars.account)

    logger.info('ProcessVars is filled')
