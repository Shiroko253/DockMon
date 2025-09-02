import os
import json

HELP_DIR = os.path.join(os.path.dirname(__file__), "language")

def get_help_text(lang_code):
    """讀取指定語言的使用說明 (默認英文)"""
    fname = f"{lang_code}.json"
    fpath = os.path.join(HELP_DIR, fname)
    if not os.path.exists(fpath):
        # fallback to en-us
        fpath = os.path.join(HELP_DIR, "en-us.json")
    try:
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)
            text = data.get("help", "")
            if not text:
                text = "\n".join(data.values())
            return text
    except Exception as e:
        return "Help document not found or failed to load.\n" + str(e)

# 可選：獲取所有語言選項（如要自動生成語言下拉選單）
def get_help_languages():
    langs = {}
    if not os.path.isdir(HELP_DIR):
        return {"English": "en-us"}
    for fname in os.listdir(HELP_DIR):
        if fname.endswith(".json"):
            code = fname.replace(".json", "")
            try:
                with open(os.path.join(HELP_DIR, fname), encoding="utf-8") as f:
                    title = json.load(f).get("title", code)
                    langs[title] = code
            except:
                langs[code] = code
    return langs
