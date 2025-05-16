import asyncio
import traceback
from common.process_vars.instance import process_vars
from common.logger import get_logger
from config.env import APP_DOMAIN
from config.texts import get_text, WELCOME_MESSAGE
from repository.chat import ChatRepository
from services.messages import send_message_or_media


async def welcome_message_job():
    while True:
        try:
            logger = get_logger(f"[{process_vars.account['username']}] [welcome_message_job]")
            chats = await ChatRepository.get_many_list(
                query={
                    "account_telegram_id": process_vars.account['telegram_id'],
                    "welcome_message": False
                }
            )

            for chat in chats:
                subscription_cancel_link = f"https://{APP_DOMAIN}/subscriptions/{chat['subscription_id']}/cancel"

                await send_message_or_media(
                    client=process_vars.client,
                    entity=chat['telegram_id'],
                    message_text=get_text(WELCOME_MESSAGE, subscription_cancel_link=subscription_cancel_link)
                )

                await ChatRepository.update_one(
                    query={'_id': chat['_id']},
                    update={'$set': {'welcome_message': True}}
                )

                logger.info(f"Welcome message successfully sent to chat {chat['telegram_id']}")

        except (Exception,):
            traceback.print_exc()

        await asyncio.sleep(2)
