import requests
import time

# --- CONFIGURATION ---
SERVER_A_URL = "http://10.0.0.10:9001/v1/chat/completions"
SERVER_B_URL = "http://10.0.0.10:9001/v1/chat/completions"

DEPTH_TEMPLATES = {
    1: "Kort en bondig. Geef alleen feitelijke antwoorden zonder uitwijdingen.",
    2: "Normale conversatie. Houd het gesprek levendig en beleefd.",
    3: "Diepgang en filosofie. Analyseer het onderwerp grondig en ga in op nuances.",
    4: "Expert niveau. Behandel het onderwerp als een specialist, met diepgaande logica.",
}


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
            return "Error: Server gaf geen geldig antwoord terug."

    except requests.exceptions.ConnectionError:
        return f"Error: Server {server_url} is niet bereikbaar."
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


def run_single_turn(topic, depth_level, history):
    """
    Voert één ronde van het gesprek uit.
    """
    system_instruction = DEPTH_TEMPLATES.get(depth_level, DEPTH_TEMPLATES[2])

    # Zorg dat system prompt in history zit als deze er nog niet is
    if not any(h.get("role") == "system" for h in history):
        history.insert(0, {"role": "system", "content": system_instruction})

    # Check of dit de eerste ronde is
    is_first_turn = len(history) <= 1

    # --- Server A Sprekt ---
    if is_first_turn:
        user_msg_a = f"Op basis van het onderwerp '{topic}', wat is jouw inbreng?"
    else:
        user_msg_a = "Wat is je volgende gedachte of inbreng op basis van het gesprek tot nu toe?"

    messages_a = [h for h in history if h.get("role") == "system"]
    messages_a.extend(history[1:])
    messages_a.append({"role": "user", "content": user_msg_a})

    response_a = send_message(SERVER_A_URL, messages_a)

    # --- Server B Sprekt ---
    user_msg_b = (
        f"Je hebt zojuist het volgende gezegd: '{response_a}'. Wat denk je hiervan?"
    )
    messages_b = [h for h in history if h.get("role") == "system"]
    messages_b.extend(history[1:])
    messages_b.append({"role": "user", "content": user_msg_b})

    response_b = send_message(SERVER_B_URL, messages_b)

    # Update history
    history.append({"role": "user", "content": user_msg_a, "display": True})
    history.append({"role": "assistant", "content": response_a, "sender": "Server A"})
    history.append({"role": "user", "content": user_msg_b, "display": False})
    history.append({"role": "assistant", "content": response_b, "sender": "Server B"})

    return history, response_a, response_b


def run_user_question(user_question, depth_level, history):
    """
    Voert een ronde uit gebaseerd op een gebruikersvraag.
    """
    system_instruction = DEPTH_TEMPLATES.get(depth_level, DEPTH_TEMPLATES[2])

    # Zorg dat system prompt in history zit als deze er nog niet is
    if not any(h.get("role") == "system" for h in history):
        history.insert(0, {"role": "system", "content": system_instruction})

    # --- Server A Sprekt ---
    messages_a = [h for h in history if h.get("role") == "system"]
    messages_a.extend(history[1:])
    messages_a.append({"role": "user", "content": user_question})

    response_a = send_message(SERVER_A_URL, messages_a)

    # --- Server B Sprekt ---
    user_msg_b = f"Je hebt zojuist het volgende gezegd: '{response_a}'. Wat denk je hiervan in relatie tot de vraag: '{user_question}'?"
    messages_b = [h for h in history if h.get("role") == "system"]
    messages_b.extend(history[1:])
    messages_b.append({"role": "user", "content": user_msg_b})

    response_b = send_message(SERVER_B_URL, messages_b)

    # Update history
    history.append({"role": "user", "content": user_question, "display": True})
    history.append({"role": "assistant", "content": response_a, "sender": "Server A"})
    history.append({"role": "user", "content": user_msg_b, "display": False})
    history.append({"role": "assistant", "content": response_b, "sender": "Server B"})

    return history, response_a, response_b
