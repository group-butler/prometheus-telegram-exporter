import sys
import os
import json
import traceback
from prometheus_client import start_http_server, Summary, Gauge
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY

import requests

try:
    TOKENS = json.loads(os.environ.get("TG_TOKENS", ""))
except ValueError as e:
    print(e)
    print(
        'Invalid or no tokens given in TG_TOKENS (Format: {"botname": "token"}). Exiting'
    )
    sys.exit(1)


class CustomCollector(object):
    def collect(self):
        webhook_enabled = GaugeMetricFamily(
            "tg_webhooks_enabled", "1 if webhooks are enabled", labels=["bot"]
        )
        custom_cert = GaugeMetricFamily(
            "tg_webhooks_custom_certificate",
            "1 if a custom certificate is set",
            labels=["bot"],
        )
        pending_updates = GaugeMetricFamily(
            "tg_webhooks_pending_update_count",
            "Number of updates awaiting delivery",
            labels=["bot"],
        )
        last_error = GaugeMetricFamily(
            "tg_webhooks_last_error_date",
            "Unix time for the most recent error that happened when "
            "trying to deliver an update via webhook",
            labels=["bot"],
        )
        max_connections = GaugeMetricFamily(
            "tg_webhooks_max_connections",
            "max number of connections for the webhook",
            labels=["bot"],
        )
        scrape_success = GaugeMetricFamily(
            "tg_webhooks_scrape_success",
            "failure of the last scrape of the telegram API",
            labels=["bot"],
        )

        for name, token in TOKENS.items():
            try:
                response = requests.get(
                    "https://api.telegram.org/bot{token}/getWebhookInfo".format(
                        token=token
                    )
                )
                data = response.json()
                print("GET {}: {}".format(name, response.status_code))
                scrape_success.add_metric([name], 1)
            except Exception as e:
                scrape_success.add_metric([name], 0)
                print("----------------")
                print("scrape exception")
                traceback.print_exc()
                print("----------------")
            else:
                webhook_enabled.add_metric([name], bool(data.get("url")))
                custom_cert.add_metric(
                    [name], data.get("has_custom_certificate", float("NaN"))
                )
                pending_updates.add_metric(
                    [name], data.get("pending_update_count", float("NaN"))
                )
                max_connections.add_metric([name], data.get("max_connections", 0))
                last_error.add_metric([name], data.get("last_error_date", 0))

        yield from (
            scrape_success,
            max_connections,
            last_error,
            pending_updates,
            custom_cert,
            webhook_enabled,
        )


REGISTRY.register(CustomCollector())

if __name__ == "__main__":
    start_http_server(8000)
    import time

    while True:
        time.sleep(10)
