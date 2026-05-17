from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="local-gpu")

response = client.chat.completions.create(
    model="qwen2.5-coder",
    messages=[{"role": "user", "content": "Write a long story about a robot learning to paint."}],
    stream=True  # Crucial for testing streaming
)

print("Assistant: ", end="")
for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)