import httpx
import logging
import json
import redis
from ..core.config import settings

logger = logging.getLogger("IAService")

class IAService:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        try:
            self.redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)
        except Exception as e:
            logger.error(f"Falha ao conectar ao Redis: {e}")
            self.redis_client = None

    async def analyze_sentiment(self, text: str) -> dict:
        # Tenta pegar do cache primeiro
        cache_key = f"sentiment:{hash(text)}"
        if self.redis_client:
            cached = self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

        prompt = f"""
        Analise o sentimento do seguinte texto relacionado ao mercado financeiro (Mini A?ndice B3).
        Responda APENAS em formato JSON com dois campos: 
        "sentiment" (valores: "bullish", "bearish", "neutral") 
        "score" (valor de 0 a 100, onde 100 A? extremamente positivo e 0 extremamente negativo).
        
        Texto: "{text}"
        """

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json"
                    }
                )
                response.raise_for_status()
                result_raw = response.json().get("response", "{}")
                result = json.loads(result_raw)
                
                # Salva no cache por 10 minutos
                if self.redis_client:
                    self.redis_client.setex(cache_key, 600, json.dumps(result))
                
                return result
            except Exception as e:
                logger.error(f"Erro ao consultar Ollama: {e}")
                return {"sentiment": "neutral", "score": 50}

# InstA?ncia Singleton
ia_service = IAService()
