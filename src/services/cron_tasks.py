import aiocron
from asyncio import create_task
from common.logger import get_logger
from common.process_vars.instance import process_vars
from jobs.outreach import outreach_job


CRON_TASKS_CONFIG = [
    {
        'job': outreach_job,
        'account_task': True,
        'cron_time': '0 */10 * * *',  # At minute 0 past every 10th hour.
    },
]


def run_cron_task_with_account(task_config: dict):
    task_name = task_config['job'].__name__.replace('_job', '')
    crontab_time = task_config['cron_time']

    args = {}

    if 'args' in task_config:
        args = task_config['args']

    args['task_name'] = task_name

    logger_prefix = f"[{process_vars.account['username']}] [cron_task_{task_name}]"
    logger = get_logger(logger_prefix)

    logger.info(f'Task {task_name} init: Cron time: {crontab_time}')

    @aiocron.crontab(crontab_time)
    async def exec_job():
        if task_name in process_vars.loop_tasks:
            logger.info(f'Task {task_name} already executing')
            return False

        task = create_task(task_config['job'](
            logger=logger,
            args=args
        ))

        process_vars.loop_tasks[task_name] = task

        logger.info(f'Started cron task')
