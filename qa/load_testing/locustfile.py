from locust import HttpUser, task, between
import json

class XiaoLeeAPIUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def test_health(self):
        self.client.get("/health")

    @task(3)
    def test_x_webhook_rate_limit(self):
        payload = {
            "direct_message_events": [
                {
                    "type": "message_create",
                    "message_create": {
                        "sender_id": f"test_user_{self.environment.runner.user_count}",
                        "message_data": {
                            "text": "Qual meu saldo na devnet?"
                        }
                    }
                }
            ]
        }
        
        # Test rate limiting by hammering the webhook
        self.client.post("/v1/integrations/x/webhook", json=payload)
