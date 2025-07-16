from platformdirs import user_data_dir
import os, json

APP_NAME = "wf-automation-app"
TOKEN_FILE = "token.json"
TOKEN_PATH = os.path.join(user_data_dir(APP_NAME), TOKEN_FILE)

def save_tokens(tokens):
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        json.dump(tokens, f)
    print(f"✅ Tokens saved to: {TOKEN_PATH}")

def load_tokens():
    if not os.path.exists(TOKEN_PATH):
        return None
    if os.path.getsize(TOKEN_PATH) == 0:
        return None
    with open(TOKEN_PATH, "r") as f:
        print(f"✅ Tokens saved to: {TOKEN_PATH}")
        try:
            data = json.load(f)
            if data is None:
                return None
            else:
                return data
        except json.JSONDecodeError:
            return None
def clear_tokens():
    with open(TOKEN_PATH, "w") as f:
        json.dump({}, f)