import asyncio
import logging
import os
import shutil
import sqlite3
from pathlib import Path
from multiprocessing import Process
from pydantic import BaseModel
from telethon.tl.types import User
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from common.db_types import AccountStatuses
from config.env import TELETHON_LOG_LEVEL
from config.system import WORK_DIR, PROCESSES
from events.new_message import new_message_to_event_pool
from jobs.welcome_message import welcome_message_job
from repository.account import AccountRepository
from common.process_vars.instance import process_vars
from repository._base_repository import BaseRepository
from jobs.events_pool import events_pool_job
from common.process_vars.init import init_process_vars
from common.logger import get_logger
from common.mongo import get_mongo_db_client
from services.cron_tasks import CRON_TASKS_CONFIG, run_cron_task_with_account


async def init_account(logger, loop) -> TelegramClient | None:
    logger.info(f"Client initialization...")

    sessions_dir = WORK_DIR / '.sessions'
    sessions_dir.mkdir(parents=True, exist_ok=True)

    general_session_file = f"{sessions_dir}/{process_vars.account['telegram_id']}.session"

    if not Path(general_session_file).exists():
        logger.error(f'Session file {general_session_file} not found, skipping')
        return

    else:
        client = get_telegram_client(
            process_vars.account,
            general_session_file.removesuffix('.session')
        )

        logging.getLogger(process_vars.account['username']).setLevel(level=TELETHON_LOG_LEVEL)

        await client.connect()

        client.add_event_handler(callback=new_message_to_event_pool, event=events.NewMessage())

        process_vars.client = client

        me = await client.get_me()

        await AccountRepository.update_one(
            {"telegram_id": process_vars.account['telegram_id']},
            {
                "$set": {
                    "phone": me.phone,
                    "premium": me.premium,
                    "username": me.username,
                    "name": f"{me.first_name} {me.last_name or ''}".strip(),
                }
            }
        )

        logger.info(f"Client connected")

        loop.create_task(events_pool_job())
        loop.create_task(welcome_message_job())

        return client


class LoginAccountBody(BaseModel):
    phone_code_hash: str | None = None
    code: int | None = None
    password: str | None = None


async def login_account(account_telegram_id: int, body: LoginAccountBody = LoginAccountBody()) -> dict:
    account = await AccountRepository.get_one({"telegram_id": account_telegram_id})
    available_statuses = [AccountStatuses.NEW, AccountStatuses.KICKED]

    if not account:
        return {
            'status': 'active',
            'error_message': 'account not found'
        }

    if account['status'] not in available_statuses:
        return {
            'success': False,
            'error_message': f'account status not in {available_statuses}'
        }

    await terminate_account_process(account_telegram_id)

    sessions_dir = Path(WORK_DIR) / '.sessions'
    sessions_dir.mkdir(parents=True, exist_ok=True)

    general_session_file = f"{sessions_dir}/{account['telegram_id']}.session"
    auth_session_file = f"{sessions_dir}/{account['telegram_id']}_auth.session"
    backup_session_file = f"{sessions_dir}/{account['telegram_id']}_bc.session"

    if Path(general_session_file).exists():
        if not Path(backup_session_file).exists():
            shutil.copy(general_session_file, backup_session_file)

        os.remove(general_session_file)

    client = get_telegram_client(account, auth_session_file.removesuffix('.session'))

    await client.connect()

    try:
        result = await client.sign_in(
            phone=account['phone'],
            phone_code_hash=body.phone_code_hash,
            code=body.code,
        )
    except SessionPasswordNeededError as err:
        result = await client.sign_in(
            password=body.password
        )

    await client.disconnect()

    if isinstance(result, User):
        shutil.copy(auth_session_file, general_session_file)
        os.remove(auth_session_file)

        if Path(backup_session_file).exists():
            general_session_connect = sqlite3.connect(general_session_file)
            general_session_cur = general_session_connect.cursor()
            general_session_cur.execute("DELETE FROM update_state")
            general_session_cur.execute("DELETE FROM entities")
            general_session_cur.execute("ATTACH DATABASE ? AS backup_session_db", (backup_session_file,))
            general_session_cur.execute("INSERT INTO update_state SELECT * FROM backup_session_db.update_state")
            general_session_cur.execute("INSERT INTO entities SELECT * FROM backup_session_db.entities")
            general_session_connect.commit()
            general_session_connect.close()

            os.remove(backup_session_file)

        update_values = {
            "status": AccountStatuses.ACTIVE
        }

        await AccountRepository.find_and_update_one(
            {'telegram_id': account['telegram_id']},
            {"$set": update_values}
        )

        return {
            'success': True,
            'stage': 'auth_success'
        }

    return {
        'success': True,
        'stage': 'code_sent',
        'phone_code_hash': result.phone_code_hash
    }


def get_telegram_client(
        account: dict,
        session_file_without_ext: str,
):
    return TelegramClient(
        session=session_file_without_ext,
        api_id=account['api_id'],
        api_hash=account['api_hash'],
        device_model=account['device_model'],
        system_version=account['system_version'],
        base_logger=account['username'],
        catch_up=True,
        sequential_updates=True
    )


def account_process(account_for_process: dict):
    process_vars.account = account_for_process
    logger = get_logger(f"[{process_vars.account['username']}]")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    BaseRepository.mongo_db_client = get_mongo_db_client()

    loop.run_until_complete(init_process_vars(logger))
    loop.run_until_complete(init_account(logger, loop))

    for cron_task_config in CRON_TASKS_CONFIG:
        if cron_task_config.get('account_task', False):
            run_cron_task_with_account(task_config=cron_task_config)

    loop.run_forever()


async def run_account_process(account: dict):
    account_telegram_id = account['telegram_id']

    PROCESSES[account_telegram_id] = Process(
        target=account_process,
        daemon=True,
        args=(account,)
    )
    PROCESSES[account_telegram_id].start()

    print(f'Account {account_telegram_id} running')

    return True


async def terminate_account_process(account_telegram_id: int):
    if account_telegram_id in PROCESSES:
        PROCESSES[account_telegram_id].terminate()
        PROCESSES.pop(account_telegram_id, None)

        print(f'Accounts {account_telegram_id} terminated')

        return True

    return False


async def terminate_all_account_processes():
    print('Run terminate_all_account_processes()')
    terminated_account_telegram_ids = []

    for account_telegram_id in list(PROCESSES.keys()):
        terminated = await terminate_account_process(account_telegram_id)

        if terminated:
            terminated_account_telegram_ids.append(account_telegram_id)

    return terminated_account_telegram_ids
