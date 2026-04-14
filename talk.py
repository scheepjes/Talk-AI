import requests
import json
import time
import sys
from colorama import init, Fore, Style

# Initialize colorama for colored output
init(autoreset=True)

# --- CONFIGURATIE ---
SERVER_A_URL = "http://10.0.0.10:9001/v1/chat/completions"
SERVER_B_URL = "http://10.0.0.10:9001/v1/chat/completions"
#
# Als je servers niet op port 8080/8090 draaien, pas dit dan aan.
# Voor oudere llama.cpp servers zonder chat API endpoint is de URL vaak: http://localhost:8080/completion

# --- Systeem Prompt Templates (Bepaalt de 'diepte' van de conversatie) ---
DEPTH_TEMPLATES = {
    1: "Kort en bondig. Geef alleen feitelijke antwoorden zonder uitweidingen.",
    2: "Normale conversatie. Houd het gesprek levendig en beleefd.",
    3: "Diepgang en filosofie. Analyseer het onderwerp grondig en ga in op nuances.",
    4: "Expert niveau. Behandel het onderwerp als een specialist, met diepgaande logica.",
}


def send_message(server_url, messages, max_tokens=16384, context_length=32000):
    """
    Verstuur een bericht naar een llama.cpp server.
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
        return (
            f"{Fore.RED}[FOUT]{Style.RESET_ALL} Server {server_url} is niet bereikbaar."
        )
    except requests.exceptions.Timeout:
        return f"{Fore.RED}[FOUT]{Style.RESET_ALL} Server time-out."
    except Exception as e:
        return f"{Fore.RED}[FOUT]{Style.RESET_ALL} Fout: {str(e)}"


def run_conversation():
    print(f"{Fore.GREEN}--- Nieuwe Conversatie Opstarten ---{Style.RESET_ALL}")

    # 1. Onderwerp vragen
    topic = input("Geef een onderwerp voor de conversatie: ").strip()
    if not topic:
        print("Geen onderwerp opgegeven. Start opnieuw.")
        return

    # 2. Diepte vragen
    print("Diepte opties:")
    print("[1] Kort & Bondig")
    print("[2] Normaal")
    print("[3] Diep & Filosofisch")
    print("[4] Expert Niveau")
    depth_input = input("Kies diepte (1-4): ").strip()

    try:
        depth_level = int(depth_input)
        if depth_level not in [1, 2, 3, 4]:
            raise ValueError
        system_instruction = DEPTH_TEMPLATES[depth_level]
    except ValueError:
        system_instruction = DEPTH_TEMPLATES[2]  # Default naar normaal
        print("Ongeldige keuze, gestandaardiseerd naar niveau 2.")

    print(
        f"{Fore.CYAN}Conversatie gestart. Onderwerp: '{topic}' | Diepte: {depth_level}{Style.RESET_ALL}"
    )

    max_turns_input = input("Maximaal aantal rondes (standaard 50): ").strip()
    try:
        max_turns_limit = int(max_turns_input) if max_turns_input else 50
        if max_turns_limit < 1:
            max_turns_limit = 50
    except ValueError:
        max_turns_limit = 50
        print("Ongeldige invoer, gestandaardiseerd naar 50 rondes.")

    print(f"Conversatie zal maximaal {max_turns_limit} rondes duren.{Style.RESET_ALL}")
    print("Druk op Ctrl+C om de conversatie te stoppen en een nieuw te starten.\n")

    # 3. Gespreksgeschiedenis inialiseren (Context)
    # System prompt definieert het gedrag van beide servers
    history = [{"role": "system", "content": system_instruction}]

    # Loop voor de conversatie
    turn_count = 0

    try:
        while True:
            # --- Server A Spreekt ---
            turn_count += 1
            if turn_count > max_turns_limit:
                print(
                    f"{Fore.YELLOW}Maximale omwentelingen bereikt. Beëindiging gesprek.{Style.RESET_ALL}"
                )
                break

            print(f"{Fore.BLUE}--- Server A spreekt ---{Style.RESET_ALL}")
            user_msg_a = f"Op basis van het onderwerp '{topic}', wat is jouw inbreng?"

            # History voor Server A: alle eerdere messages (geen reasoning)
            messages_a = [h for h in history if h.get("role") == "system"]
            messages_a.extend(
                history[1:]
            )  # Voeg alle eerdere messages toe (behalve system)
            messages_a.append({"role": "user", "content": user_msg_a})

            response_a = send_message(SERVER_A_URL, messages_a)
            print(f"{Fore.CYAN}Antwoord A: {response_a}{Style.RESET_ALL}")

            # --- Server B Spreekt ---
            print(f"{Fore.GREEN}--- Server B spreekt ---{Style.RESET_ALL}")
            user_msg_b = f"Je hebt zojuist het volgende gezegd: '{response_a}'. Wat denk je hiervan in relatie tot het onderwerp?"

            # History voor Server B: alle eerdere messages (geen reasoning)
            messages_b = [h for h in history if h.get("role") == "system"]
            messages_b.extend(
                history[1:]
            )  # Voeg alle eerdere messages toe (behalve system)
            messages_b.append({"role": "user", "content": user_msg_b})

            response_b = send_message(SERVER_B_URL, messages_b)
            print(f"{Fore.MAGENTA}Antwoord B: {response_b}{Style.RESET_ALL}")

            # Update history voor volgende ronde (alleen content, geen reasoning)
            history.append({"role": "user", "content": user_msg_a})
            history.append({"role": "assistant", "content": response_a})
            history.append({"role": "user", "content": user_msg_b})
            history.append({"role": "assistant", "content": response_b})

            # Pauze voor leesbaarheid
            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Conversatie afgebroken door gebruiker.{Style.RESET_ALL}")
    finally:
        print(f"{Fore.WHITE}Conversatie {Fore.RED}GESLOTEN{Style.RESET_ALL}")
        print(
            "Druk op Enter om een nieuw gesprek te starten, of Ctrl+C om af te sluiten."
        )
        input()


if __name__ == "__main__":
    while True:
        try:
            run_conversation()
        except KeyboardInterrupt:
            print("\nScript volledig afgesloten.")
            break
