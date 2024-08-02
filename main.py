import logging

# import logging_loki
#
# loki_handler = logging_loki.LokiHandler(
#     url="http://localhost:9010/loki/api/v1/push",
#     tags={"app": "trader"},
# )
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', force=True)

if __name__ == '__main__':
    import actor_system

    actor_system.run()
