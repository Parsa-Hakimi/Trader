from dataclasses import dataclass

from lyrid import Message

from market_repo import MarketRepository


@dataclass
class Start(Message):
    pass


@dataclass
class MarketUpdate(Message):
    market_repo: MarketRepository
    market_id: int
