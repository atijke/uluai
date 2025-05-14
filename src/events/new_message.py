import telethon
import traceback
from telethon import hints, functions, types
from telethon.events import NewMessage
from telethon.tl.types import MessageEmpty, Message
from config.texts import get_text, START_MESSAGE
from repository.event_pool import EventPoolRepository
from repository.chat import ChatRepository
from services.chats import check_entity_for_parse, formatted_and_upsert_chat
from services.messages import message_reactions_to_dict, tg_message_formatter, send_message_or_media, upsert_message
from common.process_vars.instance import process_vars
from common.logger import get_logger
from datetime import datetime, timezone
from common.helper import telethon_object_formatted, telethon_event_object_to_dict, tl_object_from_dict
from services.payments import create_subscription_link


async def new_message_to_event_pool(event: NewMessage.Event):
    logger = get_logger(f"[{process_vars.account['username']}] [new_message_to_event_pool]")

    if isinstance(event.message, MessageEmpty):
        return

    chat_telegram_id = telethon.utils.get_peer_id(event.message.peer_id)

    if await EventPoolRepository.count_documents(
        query={
            "account_telegram_id": process_vars.account['telegram_id'],
            "chat_telegram_id": chat_telegram_id,
            "event_type": 'new_message',
            "data.event.message.id": event.message.id
        }
    ):
        return

    entity = await event.message.get_chat()

    if not check_entity_for_parse(entity):
        return

    sender_entity = await event.message.get_sender()

    if sender_entity.id == process_vars.account['telegram_id']:
        return

    forwarded_sender_entity = None

    if event.message.forward:
        forwarded_sender_entity = await event.message.forward.get_sender()

        if not forwarded_sender_entity:
            forwarded_sender_entity = await event.message.forward.get_chat()

    reactions = await message_reactions_to_dict(event.message)

    logger.info(f"TELEGRAM EVENT RECEIVED [NewMessage] | Chat: {chat_telegram_id}")

    await EventPoolRepository.create_one({
        "account_telegram_id": process_vars.account['telegram_id'],
        "chat_telegram_id": chat_telegram_id,
        "event_type": 'new_message',
        "data": {
            "event": telethon_event_object_to_dict(event),
            "entity": telethon_object_formatted(entity),
            "sender_entity": telethon_object_formatted(sender_entity),
            "forwarded_sender_entity": telethon_object_formatted(forwarded_sender_entity),
            "reactions_dict": reactions
        },
        "date": datetime.now(timezone.utc),
        "status": "new"
    })

    return True


async def new_message_processing(event_pool_record: dict) -> dict:
    try:
        logger = get_logger(f"[{process_vars.account['username']}] [new_message_processing]")

        event_dict: dict = event_pool_record['data']['event']
        entity: hints.Entity = tl_object_from_dict(event_pool_record['data']['entity'])
        sender_entity: hints.Entity = tl_object_from_dict(event_pool_record['data']['sender_entity'])
        forwarded_sender_entity: hints.Entity = tl_object_from_dict(event_pool_record['data']['forwarded_sender_entity'])
        reactions_dict: dict = event_pool_record['data']['reactions_dict']
        message_obj: Message = tl_object_from_dict(event_dict['message'])

        await process_vars.client.send_read_acknowledge(
            entity=entity,
            max_id=message_obj.id,
            clear_mentions=True,
            clear_reactions=True
        )

        chat = await formatted_and_upsert_chat(
            entity=entity,
            logger=logger
        )

        if not chat.get('subscription_active'):
            subscription_link = chat.get('subscription_link')

            if not subscription_link:
                subscription_link = create_subscription_link(
                    account=process_vars.account,
                    chat_telegram_id=event_pool_record['chat_telegram_id']
                )

                chat = await ChatRepository.find_and_update_one(
                    query={'_id': chat['_id']},
                    update={'$set': {'subscription_link': subscription_link}}
                )

            send_message_response = await send_message_or_media(
                client=process_vars.client,
                entity=entity,
                message_text=get_text(START_MESSAGE, subscription_link=subscription_link)
            )

        else:

            message = await tg_message_formatter(
                message_obj=message_obj,
                sender_entity=sender_entity,
                forwarded_sender_entity=forwarded_sender_entity,
                reactions_dict=reactions_dict
            )

            after_event = await EventPoolRepository.get_one(
                query={
                    'account_telegram_id': event_pool_record['account_telegram_id'],
                    'chat_telegram_id': event_pool_record['chat_telegram_id'],
                    'event_type': 'new_message',
                    'data.event.message.id': {'$gt': message['id']}
                },
                sort={'id': -1}
            )

            if not after_event:

                await process_vars.client(functions.messages.SetTypingRequest(
                    peer=entity,
                    action=types.SendMessageTypingAction()
                ))

                answer_message_text = await process_vars.memory_manager.generate_answer(message)

                send_message_response = await send_message_or_media(
                    client=process_vars.client,
                    entity=message['chat_telegram_id'],
                    message_text=answer_message_text
                )

                answer_message_obj = await process_vars.client.get_messages(entity, ids=send_message_response['message'].id)

                answer_message = await tg_message_formatter(
                    message_obj=answer_message_obj
                )

                await upsert_message(message=message)
                await upsert_message(message=answer_message)
            else:
                await upsert_message(message=message)

            logger.info(f"SUCCESS PROCESSING MESSAGE | Chat: {message['chat_telegram_id']} | Message ID: {message['id']}")

        return {'success': True}

    except (Exception,):
        return {
            'success': False,
            'error_message': 'event processing error',
            'error_raw': traceback.format_exc()
        }
