import threading
import queue
import json
import time
import uuid
import base64
import io
import numpy as np
from PIL import Image
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import openvino as ov
import openvino_genai as ov_genai
import uvicorn

app = FastAPI()

# 1. Initialize the OpenVINO VLMPipeline on GPU
# Note: Ensure this directory exists with the converted Qwen2.5-VL model
model_path = "qwen2.5-vl-3b-instruct-openvino-int4"
print(f"Loading VLM model to Intel GPU: {model_path}...")
try:
    pipe = ov_genai.VLMPipeline(model_path, "GPU")
except Exception as e:
    print(f"Error loading model: {e}")
    print("Falling back to CPU if GPU fails...")
    pipe = ov_genai.VLMPipeline(model_path, "CPU")

def stream_tokens(user_prompt, ov_image, token_queue):
    """Background task to generate tokens and put them in the queue."""
    def streamer(token):
        token_queue.put(token)
        return False

    # Start generation with image if provided
    if ov_image is not None:
        # For Qwen2-VL family, the prompt usually needs the vision tokens if not handled by pipeline
        # But VLMPipeline usually handles the wrapping if image is passed.
        pipe.generate(user_prompt, image=ov_image, max_new_tokens=1024, streamer=streamer)
    else:
        pipe.generate(user_prompt, max_new_tokens=1024, streamer=streamer)
    
    token_queue.put(None)

def format_chat_messages(messages, model_name="qwen"):
    prompt = ""
    is_qwen = "qwen" in model_name.lower()
    
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        # Extract text content if it's a list (vision message)
        text_content = ""
        if isinstance(content, str):
            text_content = content
        elif isinstance(content, list):
            for item in content:
                if item.get("type") == "text":
                    text_content += item["text"]
        
        if is_qwen:
            prompt += f"<|im_start|>{role}\n{text_content}<|im_end|>\n"
        else: # Gemma format
            gemma_role = "model" if role == "assistant" else role
            prompt += f"<|start_of_turn|>{gemma_role}\n{text_content}<|end_of_turn|>\n"
            
    # Append the final model prompt start
    if is_qwen:
        prompt += "<|im_start|>assistant\n"
    else:
        prompt += "<|start_of_turn|>model\n"
        
    return prompt

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    
    user_prompt = ""
    ov_image = None

    if messages:
        # 1. Format the full multi-turn conversation history
        user_prompt = format_chat_messages(messages, model_name="qwen")
        
        # 2. Extract image from any message in the history
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, list):
                for item in content:
                    if item.get("type") == "image_url":
                        url = item["image_url"]["url"]
                        if url.startswith("data:image"):
                            # Handle base64 encoded image
                            try:
                                b64_data = url.split(",")[1]
                                img_bytes = base64.b64decode(b64_data)
                                pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                                img_np = np.array(pil_img)
                                ov_image = ov.Tensor(img_np)
                            except Exception as e:
                                print(f"Error decoding base64 image: {e}")
                        elif url.startswith("http"):
                            # Handle image from URL
                            try:
                                response = requests.get(url)
                                pil_img = Image.open(io.BytesIO(response.content)).convert("RGB")
                                img_np = np.array(pil_img)
                                ov_image = ov.Tensor(img_np)
                            except Exception as e:
                                print(f"Error downloading image from URL: {e}")

    request_id = f"chatcmpl-{uuid.uuid4()}"
    model_name = "qwen2.5-vl-3b-ov"

    def event_generator():
        token_queue = queue.Queue()
        thread = threading.Thread(target=stream_tokens, args=(user_prompt, ov_image, token_queue))
        thread.start()

        initial_chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model_name,
            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]
        }
        yield f"data: {json.dumps(initial_chunk)}\n\n"

        while True:
            token = token_queue.get()
            if token is None:
                break
            
            chunk = {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model_name,
                "choices": [{"index": 0, "delta": {"content": token}, "finish_reason": None}]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            token_queue.task_done()

        final_chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model_name,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
