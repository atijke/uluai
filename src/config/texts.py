def get_text(text: str, **kwargs):
    for k, v in kwargs.items():
        text = text.replace('{' + k + '}', str(v))

    return text


START_MESSAGE = 'Hi! To communicate with me, subscribe ❤️\n\n<a href="{subscription_link}">SUBSCRIBE ($50/month)</a>\n\nI\'ll send you a message right after you pay!'
WELCOME_MESSAGE = 'Subscription is now open! You can unsubscribe at <a href="{subscription_cancel_link}">this link</a>. Tell me a little about yourself 🙏'
