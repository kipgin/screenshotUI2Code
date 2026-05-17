from openai import OpenAI

# Thay bằng URL tunnel của bạn
PUBLIC_URL = "https://jpeg-travel-dozens-distributions.trycloudflare.com"  # hoặc loca.lt / trycloudflare.com

client = OpenAI(
    base_url=f"{PUBLIC_URL}/v1",
    api_key="dummy",  # vLLM không cần API key thật
)

# ===== Text-only =====
response = client.chat.completions.create(
    model="Qwen/Qwen2.5-VL-3B-Instruct",  # phải khớp với MODEL đã serve
    messages=[{"role": "user", "content": "Bạn có thể làm gì?"}],
    max_tokens=512,
)
print(response.choices[0].message.content)