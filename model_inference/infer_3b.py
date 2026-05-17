import openvino_genai as ov_genai

# 1. Path to the converted model folder
model_path = "qwen2.5_coder_3b_openvino_int4"

# 2. Initialize the pipeline on GPU
# The first time you run this, it might take a minute to 'compile' the model for your GPU
pipe = ov_genai.LLMPipeline(model_path, "GPU")

# 3. Create a simple conversation loop
def chat_with_qwen():
    print("Qwen 2.5 Coder 3B is ready! (Type 'exit' to stop)")
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