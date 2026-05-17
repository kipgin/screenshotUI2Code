import threading
import queue
import json
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import openvino_genai as ov_genai
import uvicorn

app = FastAPI()

# 1. Initialize the OpenVINO Pipeline on GPU
model_path = "qwen2.5_coder_3b_openvino_int4"
print(f"Loading model to Intel GPU: {model_path}...")
pipe = ov_genai.LLMPipeline(model_path, "GPU")

def stream_tokens(user_prompt, token_queue):
    """Background task to generate tokens and put them in the queue."""
    def streamer(token):
        # Put the token text into the queue
        token_queue.put(token)
        return False  # Return False to tell OpenVINO to keep generating

    # Start generation
    pipe.generate(user_prompt, max_new_tokens=512, streamer=streamer)
    
    # Signal that we are done
    token_queue.put(None)

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    # Get the last message content
    user_prompt = messages[-1]["content"] if messages else ""
    
    request_id = f"chatcmpl-{uuid.uuid4()}"
    model_name = "qwen2.5-coder-ov"

    def event_generator():
        token_queue = queue.Queue()
        
        # Start generation in a separate thread
        thread = threading.Thread(target=stream_tokens, args=(user_prompt, token_queue))
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
    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=8000)