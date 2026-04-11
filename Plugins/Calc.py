import re
import os

def copy_to_clipboard(text):
    os.system(f"echo {text}| clip")

def on_search(text):
    results = []
    query = text.strip()

    # Regex acts as a filter: if it doesn't look like math, skip it
    if re.match(r"^[\d\s\+\-\*\/\.\(\)\%\^\*\*]+$", query):

        # Safety: requires at least one math operator and one digit
        if any(c in "+-*/%^" for c in query) and any(c.isdigit() for c in query):
            try:
                eval_query = query.replace('^', '**')

                # Safe evaluation with no access to global variables
                result = eval(eval_query, {"__builtins__": {}}, {})

                if isinstance(result, float):
                    result = round(result, 6)  # Clean up float precision

                results.append({
                    "name": f"= {result}",
                    "score": 1000,  # High score to always appear at the top
                    "action": lambda: copy_to_clipboard(str(result)),
                    "icon_type": "calc"
                })
            except:
                pass

    return results
