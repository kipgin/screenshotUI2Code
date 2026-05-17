import asyncio
import json
import os
import shutil
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app import app
from llm.factory import set_llm_client_override
from agent.agent import AgentEvent

# Mock LLM Client that injects malformed JSON to test json_repair and fuzzy matching
class MockLLMClient:
    def __init__(self, responses: list[str]):
        self.responses = responses
        self.call_count = 0

    def build_vision_message(self, role: str, text: str, b64_image: str, media_type: str) -> dict:
        return {"role": role, "content": text}
        
    async def chat(self, messages: list[dict], **kwargs) -> str:
        # Used for git commit messages
        return "Mock Git Commit"

    async def stream_chat(self, messages: list[dict], **kwargs):
        if self.call_count >= len(self.responses):
            yield "No more mock responses"
            return
            
        resp = self.responses[self.call_count]
        self.call_count += 1
        
        # Stream it chunk by chunk
        chunk_size = 10
        for i in range(0, len(resp), chunk_size):
            yield resp[i:i+chunk_size]
            await asyncio.sleep(0.01)

async def run_e2e_test():
    print("Starting E2E API + Agent Integration Test...")
    
    # 1. Setup Mock LLM Responses
    # Turn 1: create_file with unescaped quotes and 4 spaces indentation
    turn_1_response = """\
I will create the styles.css file.
```tool_call
{
  "name": "create_file",
  "arguments": {
    "path": "styles.css",
    "content": "body {
  font-family: "Helvetica", Arial, sans-serif;
  color: red;
}"
  }
}
```"""

    # Turn 2: edit_file with fuzzy whitespace matching
    turn_2_response = """\
I will edit the styles.css file.
```tool_call
{
  "name": "edit_file",
  "arguments": {
    "path": "styles.css",
    "old_content": "  font-family: \"Helvetica\", Arial, sans-serif;\n  color: red;",
    "new_content": "  font-family: \"Roboto\";\n  color: blue;"
  }
}
```"""
    
    mock_llm = MockLLMClient([turn_1_response, turn_2_response])
    set_llm_client_override(mock_llm)

    # We use httpx.AsyncClient to hit the FastAPI app directly without starting a server
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        
        # ── Test 1: Upload Image & Initial Generation (create_file with malformed JSON) ──
        print("\\n[Test 1] Uploading image and starting initial generation...")
        
        # Create a dummy image
        dummy_img = Path("dummy.png")
        dummy_img.write_bytes(b"dummy image content")
        
        with open("dummy.png", "rb") as f:
            files = {"file": ("dummy.png", f, "image/png")}
            data = {"framework": "html/css"}
            
            async with client.stream("POST", "/api/v1/design/upload", data=data, files=files) as response:
                assert response.status_code == 200
                session_id = None
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        event_data = json.loads(line[6:])
                        if event_data["type"] == "session_id":
                            session_id = event_data["data"]
                            print(f"  -> Got session_id: {session_id}")
                        elif event_data["type"] == "tool_result":
                            res = event_data["data"]
                            print(f"  -> Tool executed: {res['tool_name']} (success: {res['success']})")
                            assert res["success"] is True
                            
        assert session_id is not None
        
        # Verify file in workspace and ensure edit_file ran successfully
        ws_path = Path("workspaces") / session_id / "styles.css"
        assert ws_path.exists()
        content = ws_path.read_text(encoding="utf-8")
        assert 'font-family: "Roboto"' in content
        assert 'color: blue;' in content
        print("[OK] Test 1 Passed: create_file and edit_file (fuzzy matching) ran successfully in a single agentic loop!")
        
        
        # ── Test 2: Multi-turn Feedback ──
        print("\\n[Test 2] Submitting feedback to verify agent exits gracefully on non-tool turn...")
        
        data2 = {"session_id": session_id, "feedback": "Looks good."}
        async with client.stream("POST", "/api/v1/design/feedback", data=data2) as response2:
            assert response2.status_code == 200
            
            async for line in response2.aiter_lines():
                if line.startswith("data: "):
                    event_data = json.loads(line[6:])
                    if event_data["type"] == "done":
                        print("  -> Agent loop finished.")

        print("[OK] Test 2 Passed: Feedback endpoint works!")
        
        
        # Cleanup
        dummy_img.unlink()
        try:
            shutil.rmtree(Path("workspaces") / session_id)
        except PermissionError:
            pass # Git sets read-only permissions on some objects on Windows
        
        print("\\n🎉 All E2E Integration Tests Passed! API, JSON Repair, and File Tools work flawlessly together.")


if __name__ == "__main__":
    asyncio.run(run_e2e_test())
