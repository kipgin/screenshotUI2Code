import re
import logging

logger = logging.getLogger(__name__)

ALL_KEYS = [
    "path",
    "content",
    "old_content",
    "new_content",
    "recursive",
    "commit_hash",
    "message",
    "workspace",
    "branch_name"
]

def extract_key_value(json_str: str, key: str, all_keys: list[str]) -> any:
    """Extract a single argument key's value safely from malformed JSON."""
    # Look for '"key"\s*:\s*"' (string values)
    pattern = re.compile(r'"' + re.escape(key) + r'"\s*:\s*"', re.DOTALL)
    match = pattern.search(json_str)
    if not match:
        # Check for boolean or number values (e.g. "recursive": true)
        bool_pattern = re.compile(r'"' + re.escape(key) + r'"\s*:\s*(true|false|\d+)', re.IGNORECASE)
        bool_match = bool_pattern.search(json_str)
        if bool_match:
            val = bool_match.group(1).lower()
            if val == 'true':
                return True
            if val == 'false':
                return False
            try:
                return int(val)
            except ValueError:
                return val
        return None

    start_pos = match.end()
    
    # 1. Find if there is another valid key AFTER this value
    next_key_idx = -1
    for k in all_keys:
        if k == key: continue
        # Look for comma, optional whitespace/newlines, and the next key
        match = re.search(r',\s*"' + re.escape(k) + r'"\s*:', json_str[start_pos:])
        if match:
            idx = start_pos + match.start()
            if next_key_idx == -1 or idx < next_key_idx:
                next_key_idx = idx
            
    if next_key_idx != -1:
        # The value ends at the last quote before the next key
        val_end = json_str.rfind('"', start_pos, next_key_idx)
        val = json_str[start_pos:val_end]
    else:
        # This is the last key in the JSON. The value ends at the absolute final quote before the closing braces.
        val_end = json_str.rfind('"')
        if val_end > start_pos:
            val = json_str[start_pos:val_end]
            # Strip trailing JSON structure if it accidentally captured it
            val = re.sub(r'"?\s*\}\s*\}?\s*$', '', val)
        else:
            val = json_str[start_pos:]
            
    # Clean up standard JSON escape characters
    val = val.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace('\\\\', '\\')
    return val


def try_parse_malformed_tool_call(json_str: str) -> dict | None:
    """Attempts to extract tool call name and arguments from malformed JSON.
    
    Fully generic and supports all tools by extracting arguments using
    separators and lookahead validation.
    """
    json_str = json_str.strip()
    
    # 1. Extract name
    name_match = re.search(r'"name"\s*:\s*"([^"]+)"', json_str)
    if not name_match:
        return None
    name = name_match.group(1)
    
    # 2. Extract all available arguments
    arguments = {}
    for key in ALL_KEYS:
        val = extract_key_value(json_str, key, ALL_KEYS)
        if val is not None:
            arguments[key] = val
            
    logger.info(f"Successfully repaired malformed tool call JSON for: {name} (keys: {list(arguments.keys())})")
    return {
        "name": name,
        "arguments": arguments
    }
