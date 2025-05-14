from enum import Enum
from fastapi import APIRouter, Depends
from api import payments


api_router = APIRouter()


class RoutesTags(str, Enum):
    PAYMENTS = 'Payments'


api_router.include_router(
    payments.router,
    prefix="/payments",
    tags=[RoutesTags.PAYMENTS]
)
