import threading
import queue
import json
import time
import uuid
import base64
import io
import numpy as np
import requests
from PIL import Image
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import openvino as ov
import openvino_genai as ov_genai
import uvicorn

app = FastAPI()

# 1. Initialize the OpenVINO VLMPipeline on GPU
model_path = r"testing_infer\gemma-3-4b-it-int4-ov"
print(f"Loading Gemma 3 VL 4B model to Intel GPU: {model_path}...")

try:
    # Use VLMPipeline for vision-language models
    pipe = ov_genai.VLMPipeline(model_path, "GPU")
except Exception as e:
    print(f"Error loading to GPU: {e}")
    print("Falling back to CPU...")
    pipe = ov_genai.VLMPipeline(model_path, "CPU")

def stream_tokens(user_prompt, ov_image, token_queue):
    """Background task to generate tokens and put them in the queue."""
    def streamer(token):
        # Put the token text into the queue
        token_queue.put(token)
        return False  # Return False to tell OpenVINO to keep generating

    # Start generation
    if ov_image is not None:
        pipe.generate(user_prompt, image=ov_image, max_new_tokens=1024, streamer=streamer)
    else:
        pipe.generate(user_prompt, max_new_tokens=1024, streamer=streamer)
    
    # Signal that we are done
    token_queue.put(None)

def format_chat_messages(messages, model_name="gemma"):
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
            # Gemma roles are: "user", "model", "system"
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
        user_prompt = format_chat_messages(messages, model_name="gemma")
        
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
    model_name = "gemma-3-4b-it-ov"

    def event_generator():
        token_queue = queue.Queue()
        
        # Start generation in a separate thread
        thread = threading.Thread(target=stream_tokens, args=(user_prompt, ov_image, token_queue))
        thread.start()

        # Send the initial role chunk
        initial_chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model_name,
            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]
        }
        yield f"data: {json.dumps(initial_chunk)}\n\n"

        # Pull tokens from the queue as they arrive
        while True:
            token = token_queue.get()
            if token is None:  # End of generation
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

        # Send final stop signal
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
    # Start the server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
