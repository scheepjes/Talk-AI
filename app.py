from flask import Flask, render_template, request, jsonify, session
from logic import (
    run_single_turn,
    run_user_question,
    DEPTH_TEMPLATES,
    SERVER_A_URL,
    SERVER_B_URL,
)
import uuid

app = Flask(__name__)
app.secret_key = "super_secret_key_for_session"  # In production, use a real secret key


@app.route("/")
def index():
    # Initialize a new session for a new conversation
    session["conversation_id"] = str(uuid.uuid4())
    session["history"] = []
    return render_template("index.html", depth_templates=DEPTH_TEMPLATES)


@app.route("/start", methods=["POST"])
def start_conversation():
    data = request.json
    topic = data.get("topic")
    depth_level = int(data.get("depth_level", 2))

    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    # Initialize history with the system prompt (handled inside run_single_turn if needed)
    # But for the web UI, we want to trigger the first turn.

    history = []
    # We use the session to store history
    session["history"] = history
    session["topic"] = topic
    session["depth_level"] = depth_level

    return jsonify({"status": "started", "topic": topic})


@app.route("/next_turn", methods=["POST"])
def next_turn():
    history = session.get("history", [])
    topic = session.get("topic")
    depth_level = session.get("depth_level")

    if not topic:
        return jsonify({"error": "No active conversation"}), 400

    try:
        new_history, resp_a, resp_b = run_single_turn(topic, depth_level, history)
        session["history"] = new_history
        session.modified = True
        return jsonify(
            {"history": new_history, "response_a": resp_a, "response_b": resp_b}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/ask_question", methods=["POST"])
def ask_question():
    data = request.json
    user_question = data.get("question")
    history = session.get("history", [])
    depth_level = session.get("depth_level")

    if not user_question:
        return jsonify({"error": "Question is required"}), 400

    try:
        new_history, resp_a, resp_b = run_user_question(
            user_question, depth_level, history
        )
        session["history"] = new_history
        session.modified = True
        return jsonify(
            {"history": new_history, "response_a": resp_a, "response_b": resp_b}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
