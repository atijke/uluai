# Ulu AI

ИИ-агент в Telegram с долгосрочной памятью.

## Локальный запуск (Python 3.11.11)
```bash
cd src/
pip install -r requirements.txt
cp .env.local.example .env
# fill: nano .env
# add account to "accounts" mongo collection
python login_account.py
python main.py
```

## Запуск через Docker
```bash
cp .env.example .env
# fill: nano .env
cp src/.env.docker.example src/.env
# fill: nano src/.env
docker compose build
docker compose up -d
# add account to "accounts" mongo collection
docker compose exec app sh
python login_account.py
exit
docker compose restart
```

## Просмотр логов
```
docker logs uluai-app-1 2>&1 -f --tail=1000
```

## Используемые технологии
- llama-index (поиск по долгосрочной памяти)
- chromadb (векторное хранение долгосрочной памяти)
- mongodb (дополнительное хранение всех сообщений, хранение чатов, аккаунтов, пула ивентов)
- stripe (оформление подписки на агент)
- telethon (работа с telegram аккаунтами)
- openai (поиск в памяти через llama-index, формирование ответа)

## Принцип работы
- Входящие сообщения складываются в пул (коллекция event_pool), после чего поочерёдно обрабатываются.
- При обработке сообщения идёт поиск релевантных сообщений из сhromadb через llama-index, используя модель embedding модель Open AI.
- Также идёт поиск последних сообщений в чате (mongodb коллекция messages).
- Формируется промпт на основе сообщения пользователя, релевантных сообщений, последних сообщений и файла персонажа (src/characters/), в котором содержится шаблон для промпта.
- Ответ извлекается из OpenAI и сообщение отправляется в чат.
- Сообщение сохраняется в долгосрочную память и в mongo.

## Хранение данных
- Сессии аккаунтов хранятся в `src/.sessions/{telegram_id}.session`
- Долгосрочная память аккаунта хранится в cromadb в `src/.memory/{telegram_id}/`
- В MongoDB хранятся также все сообщения (на текущий момент используется как краткосрочная память)
- Все чаты (юзеры) и информация о подписке stripe хранится в коллекции chats

## Файлы персонажей

Аккаунт связывается с персонажем. Все ответы строятся на основе описания личности, характера и стилей этого персонажа.

Настройки персонажей находятся в `src/characters/`.

Файловая структура:
```
...
characters/
--- ulu/
------ answer_prompt.txt
------ outreach_prompt.txt
--- alina /
------ answer_prompt.txt
------ outreach_prompt.txt
```

В промптах можно использовать макросы для автоматической подстановки информации. Список макросов:
- {relevant_messages} - список подходящих по смыслу сообщений из долгосрочной памяти
- {last_messages} - список последних сообщений из памяти
- {name} - имя собеседника
- {username} - юзернейм собеседника
- {timestamp_now} - текучая дата и время
- {query} - текст сообщения собеседника

## Функционал аутрича
Каждые N часов запускается крон задача со следующим алгоритмом:
- Поиск в монге чатов, которые имеют оплаченную подписку.
- Выборка последних сообщение из монги в этих чатах
- Запрос в llm с промптом из character/{characker_key}/outreach_prompt.txt
- Промпт составляется таким образом, что если llm считает что отвечать не нужно, ответ будет "no_message"
- Отправка сообщения или игнорирование юзера в зависимости от ответа llm

## Структура коллекций MongoDB
accounts
```
{
  "_id": {
    "$oid": "675f353fb5a944afde1b3d69"
  },
  "telegram_id": 999999,
  "name": "Ulu",
  "username": "test",
  "phone": "79999999999",
  "api_id": 999,
  "api_hash": "abc123",
  "device_model": "Huawei P30 lite",
  "system_version": "Android 9 Pie",
  "status": "new",
  "llm_settings": {
    "embed_model": "text-embedding-3-small",
    "answer_model": "gpt-5.2",
    "character": "ulu"
  }
}
```

messages
```
{
  "_id": {
    "$oid": "681dd850b03f84883f36edef"
  },
  "account_telegram_id": 8888888,
  "chat_telegram_id": 999999,
  "id": 7269,
  "message": "test",
  "date": {
    "$date": "2025-05-09T10:26:00.000Z"
  },
  ...other telethon message fields... 
}
```

chats
```
{
  "_id": {
    "$oid": "681dc305b03f84883f36dbbf"
  },
  "account_telegram_id": 88888,
  "telegram_id": 999999,
  "name": "Pavel Durov",
  "username": "durov",
  "access_hash": "-3761233432064910069",
  "subscription_link": "https://checkout.stripe.com/c/pay/cs_test_...",
  "subscription_active": true,
  "welcome_message": true
}
```

event_pool
```
{
  "account_telegram_id": 88888,
  "chat_telegram_id": 99999,
  "event_type": "new_message",
  "data": {},
  "date": {
    "$date": "2025-05-13T09:29:25.145Z"
  },
  "status": "new",
  "created_at": {
    "$date": "2025-05-13T09:29:25.145Z"
  },
  "updated_at": {
    "$date": "2025-05-13T09:29:35.354Z"
  }
}
```

## Шаблон промпта для ответа на сообщение

Данный шаблон промпта при тестировании показал себя хорошо.

```
You are an emotionally intelligent and deeply connected AI companion...

Core personality traits:
...

Communication style:
...

Guidelines:
...

Respond considering:
...

Response Guidelines:
...

---------------

Relevant messages from your dialog:
{relevant_messages}

---------------

{name} wrote you a message on Telegram.
Use relevant messages from your dialog if you need them to understand the context of the message.
Don't dwell on insignificant information from old messages, use it only if it's really important.
Experience time like a real person (every message has a time stamp).
Don't put time and name in square brackets, the reply should be your message only

---------------

Continue the dialog:

{last_messages}
[{timestamp_now}][{name}]: {query}
```

## Шаблон для аутрича

```
You're having a dialog with a user.
Your posts are marked as [You].
Feel the time like a real person. Determine the time of messages from your correspondence by the square brackets with a timestamp inside them.
The time reflects the sequence of sent messages in the chat room.
Analyze recent chat messages to see if it is necessary, appropriate, or appropriate to write another message. If you decide it is necessary, think of a simple and short message to keep the dialog going, start a new topic, or resume the conversation.

IMPORTANT! Don't make up and send a message if:
- The last post is from [you], and there are >= 2 of them.
- It is appropriate to wait for a message from a user first.
- In the context of the dialog it is not appropriate to send a message.

Response Format:
The response can be either a message or the phrase "no_message".
Don't put time and name in square brackets, the reply should be your message only.
If you decide that you don't need to send a message, the response should only contain “no_message”.

---------------

Current time: {timestamp_now}

The most recent messages of your chat:

{last_messages}
```