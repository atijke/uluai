import traceback
import stripe
from fastapi import APIRouter
from fastapi import Request
from config.env import STRIPE_WEBHOOK_SECRET
from repository.chat import ChatRepository


router = APIRouter()


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    signature = request.headers.get('stripe-signature')
    body = await request.body()

    try:
        event = stripe.Webhook.construct_event(payload=body, sig_header=signature, secret=STRIPE_WEBHOOK_SECRET)
        data = event['data']
    except Exception as e:
        traceback.print_exc()
        return e

    event_type = event['type']

    if event_type == 'customer.subscription.created':
        account_telegram_id = int(data['object']['metadata']['account_telegram_id'])
        chat_telegram_id = int(data['object']['metadata']['chat_telegram_id'])

        await ChatRepository.update_one(
            query={
                'account_telegram_id': account_telegram_id,
                'telegram_id': chat_telegram_id
            },
            update={'$set': {
                'subscription_active': True,
                'welcome_message': False
            }}
        )

        print(f"Subscription created {chat_telegram_id} (account: {account_telegram_id})")

    elif event_type == 'customer.subscription.deleted':
        account_telegram_id = int(data['object']['metadata']['account_telegram_id'])
        chat_telegram_id = int(data['object']['metadata']['chat_telegram_id'])

        await ChatRepository.update_one(
            query={
                'account_telegram_id': account_telegram_id,
                'telegram_id': chat_telegram_id
            },
            update={'$set': {'subscription_active': False}}
        )

        print(f"Subscription deleted {chat_telegram_id} (account: {account_telegram_id})")

    return {'status': 'success'}
