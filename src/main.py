#!/usr/bin/env python
import asyncio
import ngrok
import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from api import api_router
from config.env import NGROK_AUTHTOKEN, NGROK_DOMAIN, MONGO_URI
from repository.account import AccountRepository
from services.accounts import run_account_process
from common.db_types import AccountStatuses
from jobs.rotation_event_pool import rotation_event_pool_job


app = FastAPI(title="Subscription API")
app.include_router(api_router, prefix='/api/v1')
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def tunnel():
    print(f"NGROK URL: https://{NGROK_DOMAIN}")

    ngrok.forward(8000, authtoken_from_env=True, domain=NGROK_DOMAIN)

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Closing tunnel")


async def main():
    accounts = await AccountRepository.get_many_list({"status": {"$in": [AccountStatuses.ACTIVE]}})

    for account_input in accounts:
        await run_account_process(account_input)

    loop = asyncio.get_event_loop()
    rotation_event_pool_job_task = loop.create_task(rotation_event_pool_job())
    config = uvicorn.Config(app=app, port=8000)
    server = uvicorn.Server(config)

    if NGROK_AUTHTOKEN:
        tunnel_task = loop.create_task(tunnel())

    await server.serve()


if __name__ == '__main__':
    asyncio.run(main())
