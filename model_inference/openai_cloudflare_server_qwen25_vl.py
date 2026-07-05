import json
import logging
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from openai import AsyncOpenAI
import uvicorn

app = FastAPI(title="Cloudflare Qwen2.5-VL Proxy Server")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL_CLOUDFLARE = "https://webshots-somewhat-compared-hired.trycloudflare.com"
CLOUDFLARE_V1 = f"{BASE_URL_CLOUDFLARE.rstrip('/')}/v1"
MODEL_NAME = "Qwen/Qwen2.5-VL-3B-Instruct"

# Initialize Async OpenAI client pointing to Cloudflare
client = AsyncOpenAI(
    base_url=CLOUDFLARE_V1,
    api_key="dummy",
)

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    
    # Override model name to match what is served by the Cloudflare backend
    body["model"] = MODEL_NAME
    
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    temperature = body.get("temperature", 0.2)
    max_tokens = body.get("max_tokens", 4096)
    
    logger.info(f"Received completion request (stream={stream}, messages_count={len(messages)})")
    
    try:
        # Call the remote Cloudflare endpoint via async client
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            stream=stream,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        if stream:
            async def event_generator():
                async for chunk in response:
                    # Yield standard OpenAI streaming chunks
                    yield f"data: {chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"
                
            return StreamingResponse(event_generator(), media_type="text/event-stream")
        else:
            return JSONResponse(content=response.model_dump())
            
    except Exception as e:
        logger.error(f"Error calling Cloudflare Qwen endpoint: {e}")
        # Return a clean OpenAI-compatible error response
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": f"Cloudflare Proxy Error: {str(e)}",
                    "type": "internal_error",
                    "code": "cloudflare_bad_gateway"
                }
            }
        )

if __name__ == "__main__":
    logger.info(f"Starting Qwen2.5-VL Cloudflare Proxy on port 8000 targeting: {CLOUDFLARE_V1}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
