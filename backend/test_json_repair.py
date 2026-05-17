import asyncio

from utils.json_repair import try_parse_malformed_tool_call

def test_json_repair_css_quotes():
    print("Testing json_repair with unescaped quotes inside CSS...")
    
    # Simulate LLM outputting raw unescaped quotes inside the JSON string
    malformed_json = """\
{
  "name": "create_file",
  "arguments": {
    "path": "styles.css",
    "content": "body {
  font-family: "Helvetica", Arial, sans-serif;
  background-color: #f4f4f4;
}"
  }
}"""

    res = try_parse_malformed_tool_call(malformed_json)
    print("Parsed Res 1:", res)
    assert res is not None
    assert res["name"] == "create_file"
    assert res["arguments"]["path"] == "styles.css"
    
    # It must correctly capture the entire CSS block despite the unescaped quotes
    assert "font-family: \"Helvetica\"" in res["arguments"]["content"]
    assert "background-color: #f4f4f4;" in res["arguments"]["content"]
    assert "body {" in res["arguments"]["content"]
    
    print("[OK] json_repair successfully parsed CSS with unescaped quotes!")
    
    
    # Test editing with a string containing a brace near a quote
    malformed_edit_json = """\
{
  "name": "edit_file",
  "arguments": {
    "path": "styles.css",
    "old_content": "body { font-family: "Helvetica" }",
    "new_content": "body { font-family: "Arial" }"
  }
}"""
    res2 = try_parse_malformed_tool_call(malformed_edit_json)
    assert res2 is not None
    assert res2["name"] == "edit_file"
    assert "Helvetica" in res2["arguments"]["old_content"]
    assert "Arial" in res2["arguments"]["new_content"]
    
    print("[OK] json_repair successfully extracted multiple string keys with unescaped quotes!")
    print("[SUCCESS] All json_repair tests passed!")

if __name__ == "__main__":
    test_json_repair_css_quotes()
