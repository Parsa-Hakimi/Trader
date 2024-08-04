from peewee import *

db = PostgresqlDatabase('trader')


class OrderSet(Model):
    id = AutoField()
    base_token = CharField()

    class Meta:
        database = db


class Order(Model):
    identifier = CharField(primary_key=True)
    market_0 = CharField()
    market_1 = CharField()
    market_code = CharField()
    side = CharField()
    amount = DoubleField()
    price = DoubleField()
    created_at = DateTimeField()
    order_set = ForeignKeyField(OrderSet)

    class Meta:
        database = db


class OrderResult(Model):
    order = ForeignKeyField(Order, primary_key=True, unique=True)
    amount1 = DoubleField()
    amount2 = DoubleField()
    expected_gain = DoubleField()
    expected_resource = DoubleField()
    average_price = DoubleField()
    gain = DoubleField()
    resource = DoubleField()
    exchanged1 = DoubleField()
    exchanged2 = DoubleField()
    real_created_at = DateTimeField()
    closed_at = DateTimeField()

    class Meta:
        database = db

class MarketData(Model):
    market_id = IntegerField()
    market_code = CharField()
    best_bid_remain = DoubleField()
    best_bid_price = DoubleField()
    best_ask_remain = DoubleField()
    best_ask_price = DoubleField()
    update_date = DateTimeField()
    received_at = DateTimeField()

    class Meta:
        database = db
