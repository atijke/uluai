import asyncio
import telethon
from dateutil import parser
from telethon import TelegramClient, hints
from telethon.tl.types import User
from common.process_vars.instance import process_vars
from common.telethon_custom_html_parse_mode import CustomHTMLParseMode
from common.helper import telethon_object_formatted, tl_object_from_dict
from repository.message import MessageRepository


async def send_message_or_media(
        client: TelegramClient,
        entity=None,
        message_text=None,
        message_photo=None,
        parse_mode='html',
        link_preview=True,
        reply_to=None,
        schedule=None
):
    try:
        if parse_mode and parse_mode.lower() == 'html':
            parse_mode = CustomHTMLParseMode()

        if message_photo:
            message = await client.send_file(
                entity=entity,
                file=message_photo,
                caption=message_text,
                force_document=False,
                parse_mode=parse_mode,
                reply_to=reply_to
            )
        else:
            message = await client.send_message(
                entity=entity,
                message=message_text,
                reply_to=reply_to,
                parse_mode=parse_mode,
                link_preview=link_preview,
                schedule=schedule
            )

        return {
            'success': True,
            'message': message,
        }

    except Exception as err:
        error_str = str(err)

        if '400: PEER_FLOOD' in error_str or 'Too many requests (caused by SendMessageRequest)' in error_str or 'Too many requests (caused by SendMediaRequest)' in error_str:
            return {
                'success': False,
                'error_message': 'too many requests',
                'error_raw': err,
            }

        elif 'A wait of' in error_str and 'seconds is required (caused by SendMessageRequest)' in error_str:
            return {
                'success': False,
                'error_message': 'seconds is required',
                'error_raw': err,
            }

        elif '400: INPUT_USER_DEACTIVATED' in error_str or 'The specified user was deleted' in error_str:
            return {
                'success': False,
                'error_message': 'user deactivated',
                'error_raw': err,
            }

        elif '400: PEER_ID_INVALID' in error_str or 'An invalid Peer was used. Make sure to pass the right peer type and that the value is valid' in error_str:
            return {
                'success': False,
                'error_message': 'peer id invalid',
                'error_raw': err,
            }

        elif 'You can\'t write in this chat (caused by SendMessageRequest)' in error_str:
            return {
                'success': False,
                'error_message': 'forbidden to write in chat',
                'error_raw': err,
            }

        return {
            'success': False,
            'error_message': None,
            'error_raw': err,
        }


async def message_reactions_to_dict(message):
    reactions_dict = None

    if getattr(message, 'reactions', None) and message.reactions.recent_reactions:
        reactions_dict = telethon_object_formatted(message.reactions)
        tg_calls = []

        for reaction in message.reactions.recent_reactions:
            if isinstance(reaction, dict):
                reaction = tl_object_from_dict(reaction)

            tg_calls.append(process_vars.client.get_entity(reaction.peer_id))

        reactor_entities = await asyncio.gather(*tg_calls, return_exceptions=True)

        for index, reaction in enumerate(message.reactions.recent_reactions):
            reactor_peer_info_dict = {}

            if isinstance(reactor_entities[index], User):
                reactor_peer_info_dict = telethon_object_formatted(reactor_entities[index])

            reactions_dict['recent_reactions'][index]['peer_info'] = reactor_peer_info_dict

    return reactions_dict


async def tg_message_formatter(
        message_obj,
        sender_entity: hints.Entity = None,
        forwarded_sender_entity: hints.Entity = None,
        reactions_dict: dict = None
) -> dict:
    chat_telegram_id = telethon.utils.get_peer_id(message_obj.peer_id)

    if not sender_entity:
        sender_entity = await message_obj.get_sender()

    sender_dict = telethon_object_formatted(sender_entity)
    sender_dict['full_name'] = telethon.utils.get_display_name(sender_entity)

    forward_sender_dict = None

    if not forwarded_sender_entity and message_obj.forward:
        forwarded_sender_entity = await message_obj.forward.get_sender()

    if forwarded_sender_entity:
        forward_sender_dict = telethon_object_formatted(forwarded_sender_entity)
        forward_sender_dict['full_name'] = telethon.utils.get_display_name(forwarded_sender_entity)

    message_dict = telethon_object_formatted(message_obj)
    message_dict['sender'] = sender_dict
    message_dict['forwarded_sender'] = forward_sender_dict
    message_dict['chat_telegram_id'] = chat_telegram_id
    message_dict['date'] = parser.parse(message_dict['date'])
    message_dict['edit_date'] = parser.parse(message_dict['edit_date']) if 'edit_date' in message_dict and message_dict['edit_date'] else None

    message_dict['account_telegram_id'] = process_vars.account['telegram_id']

    if message_obj.media:
        if getattr(message_obj.media, 'photo', None):
            message_dict['media']['photo']['id'] = str(message_obj.media.photo.id)

            access_hash = getattr(message_obj.media.photo, 'access_hash',  None)
            message_dict['media']['photo']['access_hash'] = str(access_hash) if access_hash else None

        if getattr(message_obj.media, 'document', None):
            message_dict['media']['document']['id'] = str(message_obj.media.document.id)

            access_hash = getattr(message_obj.media.document, 'access_hash',  None)
            message_dict['media']['document']['access_hash'] = str(access_hash) if access_hash else None

    message_dict['reactions'] = reactions_dict if reactions_dict else await message_reactions_to_dict(message_obj)

    if message_obj.reply_to and hasattr(message_obj.reply_to, 'reply_to_msg_id'):
        reply_msg = await message_obj.get_reply_message()
        if getattr(reply_msg, 'message', None):
            message_dict['reply_to']['reply_to_msg'] = reply_msg.message

    return message_dict


async def upsert_message(message: dict):
    query = {
        'id': message['id'],
        'chat_telegram_id': message['chat_telegram_id'],
        'account_telegram_id': message['account_telegram_id']
    }

    created = False
    updated = False

    try:
        result = await MessageRepository.update_one(
            query,
            {'$set': message},
            upsert=True
        )

        created = bool(result.upserted_id)
        updated = result.modified_count > 0

        if created:
            process_vars.memory_manager.save_message(message=message)

    except (Exception,):
        pass

    return {
        'created': created,
        'updated': updated
    }
