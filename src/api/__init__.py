from enum import Enum
from fastapi import APIRouter, Depends
from api import payments, subscriptions


api_router = APIRouter()


class RoutesTags(str, Enum):
    PAYMENTS = 'Payments'
    SUBSCRIPTIONS = 'Subscriptions'


api_router.include_router(
    payments.router,
    prefix="/api/v1/payments",
    tags=[RoutesTags.PAYMENTS]
)

api_router.include_router(
    subscriptions.router,
    prefix="/subscriptions",
    tags=[RoutesTags.SUBSCRIPTIONS]
)
