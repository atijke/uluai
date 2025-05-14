import chromadb
from datetime import datetime, timezone
from typing import List, Dict
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.response_synthesizers import ResponseMode
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core.schema import TextNode
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter, FilterOperator
from config.env import OPENAI_API_KEY
from config.system import WORK_DIR, CHARACTERS
from repository.message import MessageRepository


class MemoryManager:
    def __init__(self, account: dict):
        self.account = account

        # Инициализация ChromaDB
        memory_dir = WORK_DIR / '.memory'
        memory_dir.mkdir(parents=True, exist_ok=True)
        account_memory_dir = f"{memory_dir}/{account['telegram_id']}"
        self.chroma_client = chromadb.PersistentClient(path=account_memory_dir)
        self.chroma_collection = self.chroma_client.get_or_create_collection("chat_memory")

        # Инициализация LlamaIndex
        self.embed_model = OpenAIEmbedding(
            model=self.account['llm_settings']['embed_model'],
            embed_batch_size=100
        )
        self.answer_model = OpenAI(
            model=self.account['llm_settings']['answer_model'],
            temperature=0.6,
            api_key=OPENAI_API_KEY
        )

        # Создание векторного хранилища
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

        # Создание индекса
        self.index = VectorStoreIndex.from_vector_store(
            self.vector_store,
            storage_context=self.storage_context,
            embed_model=self.embed_model
        )

    def replace_prompt_macros(
            self,
            prompt: str,
            query: str = '',
            relevant_messages: list = None,
            last_messages: list = None,
            sender: dict = None,
    ):
        if not relevant_messages:
            relevant_messages = []

        if not last_messages:
            last_messages = []

        relevant_messages_string = "\n".join([f"[{msg['timestamp']}][{'Ты' if msg['sender_telegram_id'] == self.account['telegram_id'] else msg['name']}]: {msg['text']}" for msg in relevant_messages])
        last_messages_string = "\n".join([f"[{msg['timestamp']}][{'Ты' if msg['sender_telegram_id'] == self.account['telegram_id'] else msg['name']}]: {msg['text']}" for msg in last_messages])

        return (
            prompt
            .replace('{relevant_messages}', relevant_messages_string)
            .replace('{last_messages}', last_messages_string)
            .replace('{query}', query)
            .replace('{name}', sender['full_name'] if sender else '')
            .replace('{username}', sender['username'] if sender else '')
            .replace('{timestamp_now}', datetime.now(timezone.utc).isoformat())
        )

    def save_message(
            self,
            message: dict
    ) -> None:
        timestamp = datetime.now().isoformat()
        metadata = {
            "account_telegram_id": self.account['telegram_id'],
            "chat_telegram_id": message['chat_telegram_id'],
            "sender_telegram_id": message['sender']['id'],
            "message_telegram_id": message['id'],
            "name": message['sender']['full_name'],
            "username": message['sender']['username'],
            "timestamp": timestamp
        }

        # Создание узла для индекса
        node = TextNode(
            text=message['message'],
            metadata=metadata
        )

        # Добавление документа в индекс
        self.index.insert_nodes([node])

    async def find_relevant_messages(
            self,
            query: str,
            chat_telegram_id: int,
            limit: int = 20
    ) -> List[Dict]:
        # Создание фильтров метаданных
        filters = MetadataFilters(
            filters=[
                MetadataFilter(
                    key="account_telegram_id",
                    operator=FilterOperator.EQ,
                    value=self.account['telegram_id']
                ),
                MetadataFilter(
                    key="chat_telegram_id",
                    operator=FilterOperator.EQ,
                    value=chat_telegram_id
                )
            ],
            condition="and"
        )

        # Создание запроса с фильтрацией по метаданным
        query_engine = self.index.as_query_engine(
            similarity_top_k=limit,
            response_mode=ResponseMode.TREE_SUMMARIZE,
            filters=filters
        )

        # Выполнение запроса
        response = query_engine.query(query)

        # Получение релевантных документов
        relevant_docs = []
        for node in response.source_nodes:
            relevant_docs.append({
                "text": node.node.text,
                "account_telegram_id": node.node.metadata['account_telegram_id'],
                "chat_telegram_id": node.node.metadata['chat_telegram_id'],
                "sender_telegram_id": node.node.metadata['sender_telegram_id'],
                "message_telegram_id": node.node.metadata['message_telegram_id'],
                "name": node.node.metadata['name'],
                "username": node.node.metadata['username'],
                "timestamp": node.node.metadata['timestamp'],
                "score": node.score
            })

        return relevant_docs

    async def find_last_messages(
            self,
            chat_telegram_id: int,
            limit: int = 10
    ) -> List[Dict]:
        messages = await MessageRepository.get_many_list(
            query={
                "account_telegram_id": self.account['telegram_id'],
                "chat_telegram_id": chat_telegram_id,
            },
            limit=limit,
            sort={"id": -1}
        )

        messages.reverse()

        result = []
        for message in messages:
            result.append({
                "text": message['message'],
                "account_telegram_id": message['account_telegram_id'],
                "chat_telegram_id": message['chat_telegram_id'],
                "sender_telegram_id": message['sender']['id'],
                "message_telegram_id": message['id'],
                "name": message['sender']['full_name'],
                "username": message['sender']['username'],
                "timestamp": message['date']
            })

        return result

    async def generate_answer(
            self,
            message: dict
    ) -> str:
        chat_telegram_id = message['sender']['id']
        relevant_messages = await self.find_relevant_messages(message['message'], chat_telegram_id)
        last_messages = await self.find_last_messages(chat_telegram_id)

        prompt = self.replace_prompt_macros(
            prompt=CHARACTERS[self.account['llm_settings']['character']]['answer_prompt'],
            query=message['message'],
            relevant_messages=relevant_messages,
            last_messages=last_messages,
            sender=message['sender']
        )

        print('')
        print('')
        print('=======================')
        print('=======LLM PROMPT======')
        print('=======================')
        print(prompt)
        print('=======================')
        print('=======================')

        response = self.answer_model.complete(prompt)

        print('')
        print('')
        print('=======================')
        print('=======LLM ANSWER======')
        print('=======================')
        print(f"{response.text}")
        print('=======================')
        print('=======================')
        print('')
        print('')

        return response.text

    async def generate_outreach(
            self,
            chat_telegram_id: int
    ) -> str:
        last_messages = await self.find_last_messages(chat_telegram_id)

        prompt = self.replace_prompt_macros(
            prompt=CHARACTERS[self.account['llm_settings']['character']]['outreach_prompt'],
            last_messages=last_messages
        )

        print('')
        print('')
        print('=======================')
        print('=======LLM PROMPT======')
        print('=======================')
        print(prompt)
        print('=======================')
        print('=======================')

        response = self.answer_model.complete(prompt)

        print('')
        print('')
        print('=======================')
        print('=======LLM ANSWER======')
        print('=======================')
        print(f"{response.text}")
        print('=======================')
        print('=======================')
        print('')
        print('')

        message_text = response.text

        return False if message_text == 'no_message' else message_text
