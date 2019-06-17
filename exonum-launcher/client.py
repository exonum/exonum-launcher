from typing import Dict

import requests
import json

from .utils import encode


class ExonumClient(object):
    TX_URL = "{}://{}:{}/api/explorer/v1/transactions"

    def __init__(
        self, hostname: str, public_api_port: int = 80, ssl: bool = False
    ) -> None:
        self.schema = "https" if ssl else "http"
        self.hostname = hostname
        self.public_api_port = public_api_port
        self.tx_url = self.TX_URL.format(
            self.schema, hostname, public_api_port)

    def send_raw_tx(self, tx: bytes) -> Dict[str, str]:
        try:
            response = requests.post(
                self.tx_url,
                data=self._msg_to_json(tx),
                headers={"content-type": "application/json"},
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def _msg_to_json(self, tx) -> str:
        return json.dumps({"tx_body": encode(tx)}, indent=4)
