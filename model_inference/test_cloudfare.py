from openai import OpenAI

# Khởi tạo client kết nối đến Kaggle qua Cloudflare
client = OpenAI(
    base_url="https://told-these-margin-operator.trycloudflare.com/v1", 
    api_key="meo-meo-123" # vLLM không check key này, điền gì cũng được
)

# Tên model PHẢI khớp chính xác với đường dẫn bạn đã chạy trong lệnh vllm ở Kaggle
MODEL_NAME = "/kaggle/input/models/google/gemma-4/transformers/gemma-4-e4b-it/1"

def chat_with_my_model(prompt):
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "Bạn là trợ lý AI được finetune để hỗ trợ lập trình."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        # In ra câu trả lời
        answer = response.choices[0].message.content
        print(f"AI: {answer}")
        
        # Phần bạn hỏi về Pricing: Lấy số token ở đây để tính tiền
        usage = response.usage
        print(f"--- Đã dùng: {usage.total_tokens} tokens ---")
        
        return answer
    except Exception as e:
        print(f"Lỗi rồi: {e}")

# Chạy thử
chat_with_my_model("Viết cho tôi một hàm Python tính giai thừa")