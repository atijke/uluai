def get_text(text: str, **kwargs):
    for k, v in kwargs.items():
        text = text.replace('{' + k + '}', str(v))

    return text


START_MESSAGE = 'Привет! Чтобы общаться со мной, оформи подписку ❤️\n\n<a href="{subscription_link}">ОФОРМИТЬ (50$/мес)</a>\n\nЯ напишу тебе сразу после оплаты!'
WELCOME_MESSAGE = f'Подписка оформлена! Расскажи немного о себе 🙏'
