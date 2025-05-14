import traceback
import telethon
from logging import Logger
from telethon.tl.functions.messages import GetPeerDialogsRequest
from telethon import TelegramClient
from telethon.tl.types import User
from common.helper import telethon_object_formatted
from common.process_vars.instance import process_vars
from repository.chat import ChatRepository


def get_username_from_entity(entity):
    username = getattr(entity, 'username', None)

    if not username:
        usernames = getattr(entity, 'usernames', None)

        if usernames and len(usernames):
            username = getattr(usernames[0], 'username', None)

    return username


def check_entity_for_parse(entity):
    return isinstance(entity, User)


async def formatted_and_upsert_chat(
        entity,
        logger: Logger,
):
    if not check_entity_for_parse(entity):
        return False

    chat_telegram_id = telethon.utils.get_peer_id(entity)

    try:
        formatted_chat = {
            'account_telegram_id': process_vars.account["telegram_id"],
            'telegram_id': chat_telegram_id,
            'name': telethon.utils.get_display_name(entity),
            'username':  get_username_from_entity(entity),
            'access_hash': str(entity.access_hash) if hasattr(entity, 'access_hash') else None,
            # 'dialog_info': await get_dialog_info(client, entity, logger)
        }

        chat = await ChatRepository.find_and_update_one(
            query={"telegram_id": chat_telegram_id},
            update={"$set": formatted_chat},
            upsert=True
        )

        logger.info(f"Chat {chat_telegram_id} successfully upsert")

        return chat

    except (Exception,) as err:
        logger.error(f"Chat {chat_telegram_id} upsert error")

        traceback.print_exc()

        return False


async def get_dialog_info(client: TelegramClient, entity, logger: Logger):
    try:
        return dialog_info_formatter(
            telethon_object_formatted(
                await client(GetPeerDialogsRequest(peers=[entity]))
            )
        )
    except (Exception,) as err:
        logger.error(err)
        return {}


def dialog_info_formatter(dialog_info: dict) -> dict:
    reactions = None

    if (len(dialog_info['messages']) > 0 and 'reactions' in dialog_info['messages'][0]
            and dialog_info['messages'][0]['reactions'] and 'results' in dialog_info['messages'][0]['reactions']
            and dialog_info['messages'][0]['reactions']['results']):
        reactions = dialog_info['messages'][0]['reactions']

    message = dialog_info['messages'][0] if dialog_info['messages'] else None

    if message and message['_'] == 'MessageEmpty':
        message = None

    return {
        'dialog': dialog_info['dialogs'][0] if dialog_info['dialogs'] else None,
        'message': message,
        'reactions': reactions,
        'chat': dialog_info['chats'][0] if dialog_info['chats'] else None,
        'user': dialog_info['users'][0] if dialog_info['users'] else None,
        'state': dialog_info['state'],
    }
