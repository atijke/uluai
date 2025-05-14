import asyncio
from services.accounts import login_account, LoginAccountBody


async def login_account_start():
    account_telegram_id = int(input('Enter account_telegram_id: '))

    result = await login_account(account_telegram_id=account_telegram_id)

    print(result)

    phone_code_hash = result['phone_code_hash']
    sms_code = int(input('Enter sms code: '))

    result = await login_account(
        account_telegram_id=account_telegram_id,
        body=LoginAccountBody(
            phone_code_hash=phone_code_hash,
            code=sms_code
        )
    )

    print(result)


asyncio.run(login_account_start())
