import requests
import time

# --- CONFIGURATION ---
SERVER_A_URL = "http://10.0.0.10:9000/v1/chat/completions"
SERVER_B_URL = "http://10.0.0.10:9001/v1/chat/completions"

# Available servers for dropdown (discovered dynamically)
AVAILABLE_SERVERS = [
    "http://10.0.0.10:9000/v1/chat/completions",
    "http://10.0.0.10:9001/v1/chat/completions",
]


def query_model_name(server_url):
    """Query a llama.cpp server for its loaded model name."""
    base_url = server_url.replace("/v1/chat/completions", "")
    models_url = f"{base_url}/v1/models"
    try:
        response = requests.get(models_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if "data" in data and len(data["data"]) > 0:
            return data["data"][0].get("id", server_url)
    except Exception:
        pass
    return server_url

DEPTH_TEMPLATES = {
    "en": {
        1: "Brief and concise. Give only factual answers without elaboration.",
        2: "Normal conversation. Keep the conversation lively and polite.",
        3: "Depth and philosophy. Analyze the subject thoroughly and explore nuances.",
        4: "Expert level. Treat the subject as a specialist, with deep logical reasoning.",
    },
    "nl": {
        1: "Kort en bondig. Geef alleen feitelijke antwoorden zonder uitwijdingen.",
        2: "Normale conversatie. Houd het gesprek levendig en beleefd.",
        3: "Diepgang en filosofie. Analyseer het onderwerp grondig en ga in op nuances.",
        4: "Expert niveau. Behandel het onderwerp als een specialist, met diepgaande logica.",
    },
}

PROMPT_TEMPLATES = {
    "en": {
        "first_turn": "Based on the topic '{topic}', what is your input?",
        "next_turn": "What is your next thought or input based on the conversation so far?",
        "server_b_react": "You just said the following: '{response_a}'. What do you think about this?",
        "server_b_question": "You just said the following: '{response_a}'. What do you think about this in relation to the question: '{user_question}'?",
    },
    "nl": {
        "first_turn": "Op basis van het onderwerp '{topic}', wat is jouw inbreng?",
        "next_turn": "Wat is je volgende gedachte of inbreng op basis van het gesprek tot nu toe?",
        "server_b_react": "Je hebt zojuist het volgende gezegd: '{response_a}'. Wat denk je hiervan?",
        "server_b_question": "Je hebt zojuist het volgende gezegd: '{response_a}'. Wat denk je hiervan in relatie tot de vraag: '{user_question}'?",
    },
}


def get_depth_template(depth_level, language="en"):
    """Get depth template for a given level and language."""
    lang_templates = DEPTH_TEMPLATES.get(language, DEPTH_TEMPLATES["en"])
    return lang_templates.get(depth_level, lang_templates[2])


def get_prompt(key, language="en"):
    """Get prompt template for a given key and language."""
    lang_prompts = PROMPT_TEMPLATES.get(language, PROMPT_TEMPLATES["en"])
    return lang_prompts.get(key, PROMPT_TEMPLATES["en"][key])


def send_message(server_url, messages, max_tokens=16384, context_length=32000):
    """
    Versstuurt een bericht naar een llama.cpp server.
    """
    try:
        payload = {
            "model": "llama",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": max_tokens,
            "stream": False,
            "context_length": context_length,
        }

        response = requests.post(server_url, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()

        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"]
        else:
            return "Error: Server did not return a valid response."

    except requests.exceptions.ConnectionError:
        return f"Error: Server {server_url} is not reachable."
    except requests.exceptions.Timeout:
        return "Error: Server time-out."
    except Exception as e:
        return f"Error: {str(e)}"


def truncate_history(history, max_messages=30):
    """
    Houd de conversaatiegeschiedenis beheersbaar.
    """
    if len(history) <= max_messages:
        return history

    system_msg = [h for h in history if h.get("role") == "system"]
    recent_messages = history[-(max_messages - len(system_msg)) :]

    return system_msg + recent_messages if system_msg else recent_messages


def run_single_turn(topic, depth_level, history, server_a_url, server_b_url, language="en"):
    """
    Execute one turn of the conversation.
    """
    system_instruction = get_depth_template(depth_level, language)

    if not any(h.get("role") == "system" for h in history):
        history.insert(0, {"role": "system", "content": system_instruction})

    is_first_turn = len([h for h in history if h.get("role") != "system"]) <= 0

    if is_first_turn:
        user_msg_a = get_prompt("first_turn", language).format(topic=topic)
    else:
        user_msg_a = get_prompt("next_turn", language)

    messages_a = [h for h in history if h.get("role") == "system"]
    messages_a.extend(history[1:])
    messages_a.append({"role": "user", "content": user_msg_a})

    response_a = send_message(server_a_url, messages_a)

    user_msg_b = get_prompt("server_b_react", language).format(response_a=response_a)
    messages_b = [h for h in history if h.get("role") == "system"]
    messages_b.extend(history[1:])
    messages_b.append({"role": "user", "content": user_msg_b})

    response_b = send_message(server_b_url, messages_b)

    history.append({"role": "user", "content": user_msg_a, "display": True})
    history.append({"role": "assistant", "content": response_a, "sender": "Server A"})
    history.append({"role": "user", "content": user_msg_b, "display": False})
    history.append({"role": "assistant", "content": response_b, "sender": "Server B"})

    return history, response_a, response_b


def run_user_question(user_question, depth_level, history, server_a_url, server_b_url, language="en"):
    """
    Execute a turn based on a user question.
    """
    system_instruction = get_depth_template(depth_level, language)

    if not any(h.get("role") == "system" for h in history):
        history.insert(0, {"role": "system", "content": system_instruction})

    messages_a = [h for h in history if h.get("role") == "system"]
    messages_a.extend(history[1:])
    messages_a.append({"role": "user", "content": user_question})

    response_a = send_message(server_a_url, messages_a)

    user_msg_b = get_prompt("server_b_question", language).format(response_a=response_a, user_question=user_question)
    messages_b = [h for h in history if h.get("role") == "system"]
    messages_b.extend(history[1:])
    messages_b.append({"role": "user", "content": user_msg_b})

    response_b = send_message(server_b_url, messages_b)

    history.append({"role": "user", "content": user_question, "display": True})
    history.append({"role": "assistant", "content": response_a, "sender": "Server A"})
    history.append({"role": "user", "content": user_msg_b, "display": False})
    history.append({"role": "assistant", "content": response_b, "sender": "Server B"})

    return history, response_a, response_b
