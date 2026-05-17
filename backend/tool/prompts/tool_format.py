"""Tool prompt: tool_format — format specification for tool call JSON blocks."""

TOOL_FORMAT: str = """\
## Tool Call Format

When you decide to use a tool, output a JSON block exactly like this:

```tool_call
{
  "name": "<tool_name>",
  "arguments": {
    "<arg1>": "<value1>",
    "<arg2>": "<value2>"
  }
}
```

### Rules
- **CRITICAL**: The code fence language MUST be exactly `tool_call` (not `json`, not `html`, not `javascript`).
- **CRITICAL**: Do NOT output raw code blocks like ```html ... ```. You MUST wrap your code inside a `create_file` tool call block!
- `name` must be one of the registered tool names.
- `arguments` must be a flat JSON object. No nesting beyond what the tool schema defines.
- Do not add any prose inside the code fence.
- You may add prose BEFORE the tool call block to explain what you are doing.
- Do NOT add prose AFTER the tool call block — wait for the tool result first.

### Example
I will create the main HTML file for the landing page:

```tool_call
{
  "name": "create_file",
  "arguments": {
    "path": "index.html",
    "content": "<!DOCTYPE html>\\n<html>...</html>"
  }
}
```
"""
