from datetime import datetime, timezone
from bson import ObjectId
from pymongo.results import UpdateResult
from common.mongo import get_mongo_db_client
from motor.motor_asyncio import AsyncIOMotorCursor, AsyncIOMotorCommandCursor


class BaseRepository:
    mongo_db_client = get_mongo_db_client()
    collection = None

    @classmethod
    async def get_one(cls, query=None, sort=None) -> dict:
        if not query:
            query = {}

        return await cls.mongo_db_client[cls.collection].find_one(
            filter=query,
            sort=sort
        )

    @classmethod
    def get_many(cls, query=None, sort=None) -> AsyncIOMotorCursor:
        if not query:
            query = {}

        return cls.mongo_db_client[cls.collection].find(
            filter=query,
            sort=sort
        )

    @classmethod
    async def get_many_list(cls, query=None, sort=None, limit: int = None) -> list:
        if not query:
            query = {}

        params = {
            'filter': query
        }

        if sort:
            params['sort'] = sort

        if limit:
            params['limit'] = limit

        return await cls.mongo_db_client[cls.collection].find(**params).to_list(length=None)

    @classmethod
    async def create_one(cls, obj: dict) -> dict:
        utc_now = datetime.utcnow()

        obj['created_at'] = utc_now
        obj['updated_at'] = utc_now

        result = await cls.mongo_db_client[cls.collection].insert_one(
            document=obj
        )

        if result and result.inserted_id:
            obj['_id'] = ObjectId(result.inserted_id)

        return obj

    @classmethod
    async def create_many(cls, objs: list[dict]) -> list[dict]:
        utc_now = datetime.now(timezone.utc)

        for i in range(len(objs)):
            objs[i]['created_at'] = utc_now
            objs[i]['updated_at'] = utc_now

        result = await cls.mongo_db_client[cls.collection].insert_many(
            documents=objs
        )

        if result and result.inserted_ids:
            i = 0

            for inserted_id in result.inserted_ids:
                objs[i]['_id'] = ObjectId(inserted_id)
                i += 1

        return objs

    @classmethod
    async def update_one(cls, query: dict, update: dict, upsert: bool = False, array_filters: list = None) -> UpdateResult:
        if not array_filters:
            array_filters = []

        update['$setOnInsert'] = {}

        if '$set' not in update:
            update['$set'] = {}

        current_time_utc = datetime.now(timezone.utc)

        update['$set']['updated_at'] = current_time_utc
        update['$setOnInsert']['created_at'] = current_time_utc

        return await cls.mongo_db_client[cls.collection].update_one(
            filter=query,
            update=update,
            upsert=upsert,
            array_filters=array_filters
        )

    @classmethod
    async def find_and_update_one(cls, query: dict, update: dict, upsert: bool = False) -> dict:
        update['$setOnInsert'] = {}

        if '$set' not in update:
            update['$set'] = {}

        current_time_utc = datetime.now(timezone.utc)

        update['$set']['updated_at'] = current_time_utc
        update['$setOnInsert']['created_at'] = current_time_utc

        return await cls.mongo_db_client[cls.collection].find_one_and_update(
            filter=query,
            update=update,
            upsert=upsert,
            return_document=True,
        )

    @classmethod
    async def update_many(cls, query: dict, update: dict) -> UpdateResult:
        if '$set' not in update:
            update['$set'] = {}

        update['$set']['updated_at'] = datetime.now(timezone.utc)

        return await cls.mongo_db_client[cls.collection].update_many(
            filter=query,
            update=update
        )

    @classmethod
    async def bulk_write(cls, requests: list) -> dict:
        return await cls.mongo_db_client[cls.collection].bulk_write(
            requests=requests,
            ordered=False
        )

    @classmethod
    async def count_documents(cls, query=None) -> int:
        if not query:
            query = {}

        return await cls.mongo_db_client[cls.collection].count_documents(
            filter=query
        )

    @classmethod
    def aggregate(cls, pipeline) -> AsyncIOMotorCommandCursor:
        return cls.mongo_db_client[cls.collection].aggregate(
            pipeline=pipeline
        )

    @classmethod
    async def aggregate_list(cls, pipeline) -> list:
        return await cls.mongo_db_client[cls.collection].aggregate(
            pipeline=pipeline
        ).to_list(length=None)

    @classmethod
    async def delete_many(cls, query):
        return await cls.mongo_db_client[cls.collection].delete_many(query)

    @classmethod
    async def delete_one(cls, query):
        return await cls.mongo_db_client[cls.collection].delete_one(query)
