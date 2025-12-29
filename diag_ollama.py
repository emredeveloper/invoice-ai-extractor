import httpx
import asyncio
import os
import base64
from dotenv import load_dotenv

load_dotenv()

async def test_lm_studio_detailed():
    env_url = os.getenv("LOCAL_LLM_URL", "http://localhost:1234/v1")
    model_name = os.getenv("LOCAL_LLM_MODEL", "qwen/qwen3-vl-4b")
    
    print("--- LM STUDIO / LOCAL LLM DIAGNOSTICS ---")
    
    async with httpx.AsyncClient() as client:
        # 1. Detect Base URL and Model
        urls_to_try = [env_url, "http://localhost:1234/v1", "http://localhost:11434/v1"]
        base_url = None
        
        for url in urls_to_try:
            try:
                print(f"Checking models at {url}...")
                resp = await client.get(f"{url}/models", timeout=2.0)
                if resp.status_code == 200:
                    base_url = url
                    available_models = [m['id'] for m in resp.json().get('data', [])]
                    print(f"[OK] Connection successful to {base_url}")
                    print(f"Available models: {available_models}")
                    break
            except Exception:
                continue
        
        if not base_url:
            print("[FAIL] Could not reach any local LLM server. Is LM Studio running and 'Local Server' started?")
            return

        print(f"Targeting model: {model_name}")
        
        # 2. Test simple completion (No vision, No JSON format)
        print(f"\nTesting simple chat with {model_name}...")
        try:
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": "hi"}],
                "temperature": 0.7
            }
            resp = await client.post(f"{base_url}/chat/completions", json=payload, timeout=30.0)
            if resp.status_code == 200:
                print(f"[OK] Simple chat works. Response: {resp.json()['choices'][0]['message']['content']}")
            else:
                print(f"[FAIL] Simple chat failed with {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"[FAIL] Simple chat error: {e}")

        # 3. Test with JSON format (Using LM Studio compatible format)
        print(f"\nTesting JSON format support (json_schema)...")
        try:
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": "Return JSON: {'test': 1}"}],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "test_schema",
                        "schema": {
                            "type": "object",
                            "properties": {"test": {"type": "number"}}
                        }
                    }
                }
            }
            resp = await client.post(f"{base_url}/chat/completions", json=payload, timeout=30.0)
            if resp.status_code == 200:
                print(f"[OK] JSON (json_schema) is supported.")
            else:
                print(f"[FAIL] JSON (json_schema) failed ({resp.status_code}).")
                print(f"Response: {resp.text}")
                print("\nTip: If both fail, we will simply omit 'response_format' and rely on the prompt.")
        except Exception as e:
            print(f"[FAIL] JSON test error: {e}")

if __name__ == "__main__":
    asyncio.run(test_lm_studio_detailed())
