import json
import os

def load_cookies(file_name: str = "twitter_manual_cookies.json"):
    """
    Loads cookies from a specified JSON file within the data directory.
    Uses relative pathing to be callable from any script inside the scripts/ folder.
    """
    relative_path = os.path.join('data', file_name)
    
    try:
        with open(relative_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Cookie file not found at {relative_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {relative_path}")
        return None

def load_cookies_from_data(file_name: str = "twitter_manual_cookies.json"):
    """
    Loads cookies from the 'data' directory.
    This assumes the script is being run from the project root.
    """
    file_path = os.path.join('data', file_name)
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Cookie file not found at {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
        return None 