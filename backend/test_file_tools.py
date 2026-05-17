import asyncio
import shutil
from pathlib import Path

from tool.file_tools import read_file, edit_file
from tool.schema import ToolResult

async def test_file_tools():
    print("Running file_tools fuzzy editing tests...")
    
    workspace = Path("test_workspace")
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    
    test_file = "hello.html"
    test_path = workspace / test_file
    
    # 1. Create HTML file
    initial_content = """\
<html>
  <body>
    <form>
      <label>Login</label>
      <input type="text">
    </form>
  </body>
</html>"""
    test_path.write_text(initial_content, encoding="utf-8")
    
    # 2. Test edit_file with EXACT match
    exact_old = "      <label>Login</label>"
    res: ToolResult = await edit_file(test_file, exact_old, "      <label>Sign In</label>", str(workspace))
    assert res.success
    print("[OK] edit_file successfully replaced with EXACT match!")
    
    # 3. Test edit_file with FUZZY match (wrong indentation and extra trailing spaces)
    fuzzy_old = """
<form>
  <label>Sign In</label>
  <input type="text">    
</form>
"""
    new_content = """\
    <form>
      <label>Username</label>
      <input type="text">
      <label>Password</label>
      <input type="password">
    </form>"""
    
    res = await edit_file(test_file, fuzzy_old, new_content, str(workspace))
    assert res.success
    content = test_path.read_text(encoding="utf-8")
    assert "<label>Username</label>" in content
    print("[OK] edit_file successfully replaced with FUZZY whitespace match!")
    
    # Cleanup
    shutil.rmtree(workspace)
    print("[SUCCESS] All file tool fuzzy editing tests passed!")

if __name__ == "__main__":
    asyncio.run(test_file_tools())
