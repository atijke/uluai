import stripe
from config.env import STRIPE_SECRET_KEY, STRIPE_PRICE_ID


stripe.api_key = STRIPE_SECRET_KEY


def create_subscription_link(
        account: dict,
        chat_telegram_id: int
):
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price': STRIPE_PRICE_ID,
            'quantity': 1,
        }],
        mode='subscription',
        success_url=f"https://t.me/{account['username']}",
        cancel_url=f"https://t.me/{account['username']}",
        subscription_data={
            'metadata': {
                'account_telegram_id': str(account['telegram_id']),
                'chat_telegram_id': str(chat_telegram_id)
            }
        }
    )

    return checkout_session.url
