import re

def extract_web_code(text):
    """
    Extracts HTML, CSS, and JS from markdown blocks and wraps them 
    into a single valid HTML string for an iframe.
    """
    # Regex to find content inside ```html ... ```, etc.
    html_match = re.search(r"```html\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    css_match = re.search(r"```css\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    js_match = re.search(r"```(?:javascript|js)\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)

    html_content = html_match.group(1) if html_match else ""
    css_content = css_match.group(1) if css_match else ""
    js_content = js_match.group(1) if js_match else ""

    if not html_content and not css_content and not js_content:
        return None

    # Construct a full standalone HTML document
    full_html = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <style>{css_content}</style>
        </head>
        <body>
            {html_content}
            <script>{js_content}</script>
        </body>
    </html>
    """
    return full_html