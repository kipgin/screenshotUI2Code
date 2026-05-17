import openvino_genai as ov_genai

model_path = "qwen2.5_coder_7b_openvino_int4"


pipe = ov_genai.LLMPipeline(model_path, "GPU")

def chat_with_qwen():
    print("Qwen 2.5 Coder 7B is ready! (Type 'exit' to stop)")
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            break
        
        print("Assistant: ", end="", flush=True)
        
        # Stream the output for a 'typing' effect
        pipe.generate(user_input, max_new_tokens=512, streamer=lambda token: print(token, end="", flush=True))
        print("\n")

if __name__ == "__main__":
    chat_with_qwen()