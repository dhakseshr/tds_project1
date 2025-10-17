import os
import base64
import mimetypes
from pathlib import Path
from datetime import datetime

# Use the Gemini / Google GenAI SDK
# Install via: pip install google-genai
from google import genai
from google.genai import types

# Load environment variables (e.g. from .env)
from dotenv import load_dotenv
load_dotenv()

# Read your Gemini API key (you may store it e.g. as GEMINI_API_KEY)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Please set GEMINI_API_KEY in your environment")

# Configure the genai client
genai.configure(api_key=GEMINI_API_KEY)
client = genai.Client()

# Directory for saving attachments
TMP_DIR = Path("/tmp/llm_attachments")
TMP_DIR.mkdir(parents=True, exist_ok=True)


def decode_attachments(attachments):
    """
    attachments: list of {name, url: data:<mime>;base64,<b64>}
    Saves files into /tmp/llm_attachments/<name>
    Returns list of dicts: {"name": name, "path": "/tmp/..", "mime": mime, "size": n}
    """
    saved = []
    for att in attachments or []:
        name = att.get("name") or "attachment"
        url = att.get("url", "")
        if not url.startswith("data:"):
            continue
        try:
            header, b64data = url.split(",", 1)
            mime = header.split(";")[0].replace("data:", "")
            data = base64.b64decode(b64data)
            path = TMP_DIR / name
            with open(path, "wb") as f:
                f.write(data)
            saved.append({
                "name": name,
                "path": str(path),
                "mime": mime,
                "size": len(data)
            })
        except Exception as e:
            print("Failed to decode attachment", name, e)
    return saved


def summarize_attachments_meta(saved):
    """
    saved is list from decode_attachments.
    Returns a short human-readable summary string for the prompt.
    """
    lines = []
    for s in saved:
        nm = s["name"]
        p = s["path"]
        mime = s.get("mime", "")
        try:
            if mime.startswith("text") or nm.endswith((".md", ".txt", ".json", ".csv")):
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    if nm.endswith(".csv"):
                        # read first few lines
                        preview_lines = []
                        for _ in range(3):
                            try:
                                preview_lines.append(next(f).strip())
                            except StopIteration:
                                break
                        preview = "\\n".join(preview_lines)
                    else:
                        data = f.read(1000)
                        preview = data.replace("\n", "\\n")[:1000]
                lines.append(f"- {nm} ({mime}): preview: {preview}")
            else:
                lines.append(f"- {nm} ({mime}): {s['size']} bytes")
        except Exception as e:
            lines.append(f"- {nm} ({mime}): (could not read: {e})")
    return "\\n".join(lines)


def _strip_code_block(text: str) -> str:
    """If text is inside triple-backticks, return the inner portion; else return as-is."""
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            return parts[1].strip()
    return text.strip()


def generate_readme_fallback(brief: str, checks=None, attachments_meta=None, round_num=1):
    checks_text = "\\n".join(checks or [])
    att_text = attachments_meta or ""
    return f"""# Auto-generated README (Round {round_num})

**Project brief:** {brief}

**Attachments:**
{att_text}

**Checks to meet:**
{checks_text}

## Setup
1. Open `index.html` in a browser.
2. No build steps required.

## Notes
This README was generated as a fallback (Gemini did not return an explicit README).
"""


def generate_app_code(brief: str, attachments=None, checks=None,
                      round_num=1, prev_readme=None):
    """
    Generate (or revise) an app using Gemini.

    - round_num=1: build from scratch
    - round_num=2: refactor based on new brief and previous README/code
    """
    saved = decode_attachments(attachments or [])
    attachments_meta = summarize_attachments_meta(saved)

    context_note = ""
    if round_num == 2 and prev_readme:
        context_note = (
            f"\n### Previous README.md:\n{prev_readme}\n\n"
            "Revise and enhance this project according to the new brief below.\n"
        )

    # Build the user prompt to send to Gemini
    user_prompt = f"""
You are a professional web developer assistant.

### Round
{round_num}

### Task
{brief}

{context_note}

### Attachments (if any)
{attachments_meta}

### Evaluation checks
{checks or []}

### Output format rules:
1. Produce a complete web app (HTML/JS/CSS inline if needed) satisfying the brief.
2. Output must contain **two parts only**:
   - index.html (main code)
   - README.md (starts after a line containing exactly: ---README.md---)
3. README.md must include:
   - Overview
   - Setup
   - Usage
   - If Round 2, describe improvements made from previous version.
4. Do not include any commentary outside code or README.
"""

    model_name = "gemini-1.5-flash"
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=user_prompt
        )
        text = response.text or ""
        print("✅ Generated code using Gemini API.")
    except Exception as e:
        print("⚠ Gemini API failed, using fallback HTML instead:", e)
        text = f"""
<html>
  <head><title>Fallback App</title></head>
  <body>
    <h1>Hello (fallback)</h1>
    <p>This is fallback because Gemini failed. Brief: {brief}</p>
  </body>
</html>

---README.md---
{generate_readme_fallback(brief, checks, attachments_meta, round_num)}
"""

    if "---README.md---" in text:
        code_part, readme_part = text.split("---README.md---", 1)
        code_part = _strip_code_block(code_part)
        readme_part = _strip_code_block(readme_part)
    else:
        code_part = _strip_code_block(text)
        readme_part = generate_readme_fallback(brief, checks, attachments_meta, round_num)

    files = {"index.html": code_part, "README.md": readme_part}
    return {"files": files, "attachments": saved}
