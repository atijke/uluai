import asyncio
import traceback
from random import randint
from common.db_types import EventPoolStatuses
from events.new_message import new_message_processing
from repository.event_pool import EventPoolRepository
from common.process_vars.instance import process_vars
from common.logger import get_logger, send_alert_to_telegram_chat


EVENT_POOL_TYPES = {
    'new_message': {
        'callback': new_message_processing,
        'only_last_event': False
    }
}


async def events_pool_job():
    processing_chat_telegram_id = None

    await asyncio.sleep(randint(1, 5))

    while True:
        try:
            logger = get_logger(f"[{process_vars.account['username']}] [events_pool_job]")
            event_pool = await EventPoolRepository.get_many_list(
                query={
                    "account_telegram_id": process_vars.account['telegram_id'],
                    "event_type": {"$in": list(EVENT_POOL_TYPES.keys())},
                    "status": EventPoolStatuses.NEW
                },
                sort={'created_at': 1}
            )

            event_pool_dict = {}

            for event_in_pool in event_pool:
                chat_telegram_id = event_in_pool['chat_telegram_id']
                event_type = event_in_pool['event_type']

                if chat_telegram_id not in event_pool_dict:
                    event_pool_dict[chat_telegram_id] = {}

                if event_type not in event_pool_dict[chat_telegram_id]:
                    event_pool_dict[chat_telegram_id][event_type] = []

                event_pool_dict[chat_telegram_id][event_type].append(event_in_pool)

            logger.info(f"Events pool length: {len(event_pool_dict)}")

            for chat_telegram_id in list(event_pool_dict):
                processing_chat_telegram_id = chat_telegram_id

                for event_pool_type in list(EVENT_POOL_TYPES):
                    if (
                            event_pool_type in event_pool_dict[chat_telegram_id] and
                            len(event_pool_dict[chat_telegram_id][event_pool_type])
                    ):
                        events_in_pool = event_pool_dict[chat_telegram_id][event_pool_type]
                        only_last_event = EVENT_POOL_TYPES[event_pool_type].get('only_last_event', False)
                        start_event_index = len(events_in_pool) - 1 if only_last_event else 0

                        for event_index in range(start_event_index, len(events_in_pool)):
                            event_pool_record = events_in_pool[event_index]
                            is_skip = False

                            if only_last_event:
                                if await EventPoolRepository.get_one(
                                    query={
                                        "account_telegram_id": event_pool_record['account_telegram_id'],
                                        "chat_telegram_id": event_pool_record['chat_telegram_id'],
                                        "event_type": event_pool_record['event_type'],
                                        "status": {'$ne': 'new'},
                                        "date": {"$gt": event_pool_record['date']}
                                    }
                                ):
                                    is_skip = True

                            result_callback = None
                            result_callback_error = None

                            if is_skip:
                                await EventPoolRepository.update_one(
                                    query={"_id": event_pool_record['_id']},
                                    update={"$set": {
                                        'status': EventPoolStatuses.SKIP,
                                        'skip_info': 'there was already an event after'
                                    }}
                                )

                            else:
                                try:
                                    result_callback = await EVENT_POOL_TYPES[event_pool_type]['callback'](event_pool_record)
                                except (Exception,) as err:
                                    result_callback_error = str(err)

                                if result_callback and result_callback['success']:
                                    update_data = {"status": EventPoolStatuses.SUCCESS}

                                    if 'status' in result_callback:
                                        update_data['status'] = result_callback['status']

                                    if 'skip_info' in result_callback:
                                        update_data['skip_info'] = result_callback['skip_info']

                                    await EventPoolRepository.update_one(
                                        query={"_id": event_pool_record['_id']},
                                        update={"$set": update_data}
                                    )

                                else:
                                    await EventPoolRepository.update_one(
                                        query={"_id": event_pool_record['_id']},
                                        update={"$set": {
                                            "status": EventPoolStatuses.ERROR,
                                            "error": result_callback['error_raw'] if result_callback else result_callback_error
                                        }}
                                    )

                                    await send_alert_to_telegram_chat(
                                        level_name='events_pool_processing_job',
                                        args={
                                            "account": {
                                                "telegram_id": process_vars.account['telegram_id'],
                                                "username": process_vars.account['username']
                                            },
                                            "chat_telegram_id": processing_chat_telegram_id,
                                            "event_pool_id": str(event_pool_record['_id'])
                                        },
                                        err_message=result_callback['error_raw'] if result_callback else result_callback_error
                                    )

                            if only_last_event:
                                await EventPoolRepository.update_many(
                                    query={
                                        "account_telegram_id": process_vars.account['telegram_id'],
                                        "chat_telegram_id": chat_telegram_id,
                                        "event_type": event_pool_type,
                                        "status": EventPoolStatuses.NEW
                                    },
                                    update={"$set": {"status": EventPoolStatuses.SKIP}}
                                )

        except (Exception,):
            await send_alert_to_telegram_chat(
                level_name='events_pool_processing_job',
                args={
                    "account": {
                        "telegram_id": process_vars.account['telegram_id'],
                        "username": process_vars.account['username']
                    },
                    "chat_telegram_id": processing_chat_telegram_id
                },
                err_message=traceback.format_exc()
            )

        await asyncio.sleep(2)
