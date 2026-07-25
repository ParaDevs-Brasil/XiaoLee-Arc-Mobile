from locust import HttpUser, task, between
import random
import uuid

# Uma lista pequena de usuários para forçar o Rate Limiting (limite é 60/min por user_id)
# Com 10 usuários e dezenas de instâncias rodando simultaneamente, 
# a cota de 60 requisições/minuto vai se esgotar em segundos, resultando em 429s.
USER_IDS = [f"locust_tester_{i}" for i in range(1, 11)]

INTENT_SAMPLES = [
    "Qual é o meu saldo?",
    "Quero fazer um swap de 5 USDC pra SOL",
    "Preciso de uma cotação de SOL pra USDC",
    "Como usar a plataforma?",
    "Troca 100 USDC pra mim",
]

class XiaoLeeUser(HttpUser):
    # Tempo de espera mínimo entre cada request de um único usuário virtual.
    # Colocando entre 0 e 1 segundo, cada usuário virtual fará muitos requests rápidos.
    wait_time = between(0.1, 0.5)

    @task
    def send_chat_message(self):
        user_id = random.choice(USER_IDS)
        message = random.choice(INTENT_SAMPLES)
        
        payload = {
            "message": message,
            "user_id": user_id,
            "platform": "locust_test"
        }
        
        # Realiza a requisição e checa o retorno
        with self.client.post("/chat", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                # 429 é o comportamento ESPERADO do nosso sistema de segurança, 
                # então podemos marcar como "sucesso" na validação de rate limit,
                # mas no Locust geralmente marcamos como falha para ver no gráfico.
                response.failure("Rate Limit Exceeded (429) - Segurança Funcionando!")
            elif response.status_code == 500:
                response.failure(f"Internal Server Error: {response.text}")
            else:
                response.failure(f"Unexpected status: {response.status_code}")
