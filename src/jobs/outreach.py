import traceback
from logging import Logger
from common.process_vars.instance import process_vars
from repository.chat import ChatRepository
from services.messages import upsert_message, tg_message_formatter, send_message_or_media


async def outreach_job(
        logger: Logger,
        args: dict
):
    try:
        chats = await ChatRepository.get_many_list({
            'account_telegram_id': process_vars.account['telegram_id'],
            'subscription_active': True,
        })

        for chat in chats:
            chat_telegram_id = chat['telegram_id']

            try:
                outreach_message_text = await process_vars.memory_manager.generate_outreach(chat_telegram_id=chat_telegram_id)

                if outreach_message_text:
                    send_message_response = await send_message_or_media(
                        client=process_vars.client,
                        entity=chat_telegram_id,
                        message_text=outreach_message_text
                    )

                    answer_message_obj = await process_vars.client.get_messages(chat_telegram_id, ids=send_message_response['message'].id)

                    answer_message = await tg_message_formatter(message_obj=answer_message_obj)

                    await upsert_message(message=answer_message)

                    logger.info(f'Outreach chat {chat_telegram_id}. Success sent message')

                else:
                    logger.info(f'Outreach chat {chat_telegram_id}. Skip. No need')

            except Exception as err:
                traceback.print_exc()

                logger.error(f"Outreach chat {chat_telegram_id}. Error message: {err}")

        return True

    except Exception as err:
        traceback.print_exc()

        logger.error(f"Message: {err}")

        return False

    finally:
        logger.info("Finished cron task")

        if args['task_name'] in process_vars.loop_tasks:
            del process_vars.loop_tasks[args['task_name']]
