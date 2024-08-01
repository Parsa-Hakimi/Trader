from prometheus_client import Counter, Gauge, Histogram, Summary

best_price = Gauge("best_price", "Best price for a market", labelnames=['market', 'type'])
best_amount = Gauge("best_amount", "Best amount for a market", labelnames=['market', 'type'])

calc_duration = Summary("calc_duration", "Duration of calculation + order placement")
order_placement_duration = Summary("order_duration", "Duration of order placement")

market_update_delay = Histogram('market_update_delay_seconds',
                                'Delay of market update messages arriving in the websocket',
                                labelnames=['market'])
proxy_requests = Counter('proxy_requests', "State of requests sent",
                         labelnames=['path', 'method', 'status_code', 'retry'])
