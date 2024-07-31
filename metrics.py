from prometheus_client import Counter, Gauge

best_price = Gauge("best_price", "Best price for a market", labelnames=['market', 'type'])
best_amount = Gauge("best_amount", "Best amount for a market", labelnames=['market', 'type'])
