import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

class BigiSubClient:
    BASE_URL = "https://api.bigisub.com/v1"  # Replace with actual API production endpoint

    def __init__(self):
        self.api_key = getattr(settings, 'BIGISUB_API_KEY', '')
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }

    def _post(self, endpoint, data):
        url = f"{self.BASE_URL}/{endpoint}"
        if not self.api_key or "mock" in self.api_key.lower():
            # Dev simulation mode
            logger.info(f"[SIMULATED] BigiSub API Call to {url} with payload {data}")
            return {
                "status": "success",
                "message": "Transaction successful (Simulated)",
                "data": {
                    "reference": "BIGI-MOCK-REF-" + str(data.get("phone", "08000000000")),
                    "amount": data.get("amount", 100),
                    "network": data.get("network"),
                    "api_response": {"status_code": 200, "detail": "Simulation success"}
                }
            }
        
        try:
            logger.info(f"Dispatching API call to BigiSub: {url}")
            response = requests.post(url, json=data, headers=self.headers, timeout=30)
            logger.info(f"BigiSub response status code: {response.status_code}")
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error(f"BigiSub error response: {response.text}")
                return {
                    "status": "failed",
                    "message": f"API returned status {response.status_code}",
                    "details": response.text
                }
        except requests.RequestException as e:
            logger.exception("BigiSub API Request Connection Failure")
            return {
                "status": "failed",
                "message": f"Connection timed out or failed: {str(e)}"
            }

    def purchase_airtime(self, phone, network, amount):
        payload = {
            "service_type": "airtime",
            "phone": phone,
            "network": network,
            "amount": int(amount)
        }
        return self._post("purchase/airtime/", payload)

    def purchase_data(self, phone, network, plan_code):
        payload = {
            "service_type": "data",
            "phone": phone,
            "network": network,
            "plan_code": plan_code
        }
        return self._post("purchase/data/", payload)
