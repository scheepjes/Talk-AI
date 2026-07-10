from flask import Flask, render_template, request, jsonify, session
from logic import (
    run_single_turn,
    run_user_question,
    DEPTH_TEMPLATES,
    get_depth_template,
    SERVER_A_URL,
    SERVER_B_URL,
    AVAILABLE_SERVERS,
    query_model_name,
)
from database import (
    save_conversation,
    save_message,
    get_all_conversations,
    get_conversation_messages,
    delete_conversation,
    delete_all_conversations,
)

import uuid

def get_conv_from_db(conversation_id):
    """Get conversation metadata from database as dict."""
    conversations = get_all_conversations()
    conv = next((c for c in conversations if c["id"] == conversation_id), None)
    return dict(conv) if conv else None

app = Flask(__name__)
app.secret_key = "super_secret_key_for_session"  # In production, use a real secret key


@app.route("/")
def index():
    if "conversation_id" not in session:
        session["conversation_id"] = str(uuid.uuid4())
    if "language" not in session:
        session["language"] = "en"
    server_models = {url: query_model_name(url) for url in AVAILABLE_SERVERS}
    return render_template(
        "index.html",
        depth_templates_en=DEPTH_TEMPLATES.get("en", {}),
        depth_templates_nl=DEPTH_TEMPLATES.get("nl", {}),
        language=session["language"],
        db_enabled=True,
        server_a_url=SERVER_A_URL,
        server_b_url=SERVER_B_URL,
        server_models=server_models,
    )


@app.route("/start", methods=["POST"])
def start_conversation():
    data = request.json
    topic = data.get("topic")
    depth_level = int(data.get("depth_level", 2))
    language = data.get("language", session.get("language", "en"))
    server_a_url = data.get("server_a_url", SERVER_A_URL)
    server_b_url = data.get("server_b_url", SERVER_B_URL)

    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    session["conversation_id"] = str(uuid.uuid4())
    session["topic"] = topic
    session["depth_level"] = depth_level
    session["language"] = language
    session["server_a_url"] = server_a_url
    session["server_b_url"] = server_b_url
    session.modified = True

    save_conversation(session["conversation_id"], topic, depth_level, server_a_url, server_b_url, language)

    return jsonify(
        {
            "status": "started",
            "topic": topic,
            "conversation_id": session["conversation_id"],
        }
    )


@app.route("/next_turn", methods=["POST"])
def next_turn():
    data = request.json or {}
    conversation_id = data.get("conversation_id")

    topic = session.get("topic")
    depth_level = session.get("depth_level")
    language = data.get("language") or session.get("language", "en")
    server_a_url = data.get("server_a_url") or session.get("server_a_url", SERVER_A_URL)
    server_b_url = data.get("server_b_url") or session.get("server_b_url", SERVER_B_URL)

    if not conversation_id:
        conversation_id = session.get("conversation_id")

    if conversation_id:
        session["conversation_id"] = conversation_id
        session.modified = True

    if not topic and conversation_id:
        conv = get_conv_from_db(conversation_id)
        if conv:
            topic = conv["topic"]
            depth_level = conv.get("depth_level", depth_level)
            session["topic"] = topic
            session["depth_level"] = depth_level
            if conv.get("server_a_url"):
                session["server_a_url"] = conv["server_a_url"]
            if conv.get("server_b_url"):
                session["server_b_url"] = conv["server_b_url"]
            if conv.get("language"):
                session["language"] = conv["language"]
            session.modified = True

    if not topic:
        return jsonify({"error": "No active conversation"}), 400

    try:
        db_messages = (
            get_conversation_messages(conversation_id) if conversation_id else []
        )
        history = [
            {
                "role": msg["role"],
                "content": msg["content"],
                "sender": msg["sender"],
                "display": bool(msg["display"]),
            }
            for msg in db_messages
        ]
        system_instruction = get_depth_template(depth_level, language)
        if not any(h.get("role") == "system" for h in history):
            history.insert(0, {"role": "system", "content": system_instruction})

        old_content_count = len(history)

        new_history, resp_a, resp_b = run_single_turn(topic, depth_level, history, server_a_url, server_b_url, language)

        for msg in new_history[old_content_count:]:
            save_message(
                conversation_id,
                msg.get("role"),
                msg.get("content"),
                msg.get("sender"),
                msg.get("display", True),
            )

        return jsonify(
            {"history": new_history, "response_a": resp_a, "response_b": resp_b}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/ask_question", methods=["POST"])
def ask_question():
    data = request.json or {}
    user_question = data.get("question")
    conversation_id = data.get("conversation_id")
    depth_level = session.get("depth_level")
    language = data.get("language") or session.get("language", "en")
    server_a_url = data.get("server_a_url") or session.get("server_a_url", SERVER_A_URL)
    server_b_url = data.get("server_b_url") or session.get("server_b_url", SERVER_B_URL)

    if not user_question:
        return jsonify({"error": "Question is required"}), 400

    if not conversation_id:
        conversation_id = session.get("conversation_id")

    if conversation_id:
        session["conversation_id"] = conversation_id
        session.modified = True

    if not depth_level and conversation_id:
        conv = get_conv_from_db(conversation_id)
        if conv:
            depth_level = conv.get("depth_level")
            session["depth_level"] = depth_level
            session.modified = True

    try:
        db_messages = (
            get_conversation_messages(conversation_id) if conversation_id else []
        )
        history = [
            {
                "role": msg["role"],
                "content": msg["content"],
                "sender": msg["sender"],
                "display": bool(msg["display"]),
            }
            for msg in db_messages
        ]
        system_instruction = get_depth_template(depth_level, language)
        if not any(h.get("role") == "system" for h in history):
            history.insert(0, {"role": "system", "content": system_instruction})

        old_content_count = len(history)

        new_history, resp_a, resp_b = run_user_question(
            user_question, depth_level, history, server_a_url, server_b_url, language
        )

        for msg in new_history[old_content_count:]:
            save_message(
                conversation_id,
                msg.get("role"),
                msg.get("content"),
                msg.get("sender"),
                msg.get("display", True),
            )

        return jsonify(
            {"history": new_history, "response_a": resp_a, "response_b": resp_b}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/set_language", methods=["POST"])
def set_language():
    """Set the UI language preference."""
    data = request.json or {}
    language = data.get("language", "en")
    if language not in ("en", "nl"):
        language = "en"
    session["language"] = language
    session.modified = True
    return jsonify({"status": "ok", "language": language})


@app.route("/api/conversations", methods=["GET"])
def get_conversations():
    """Get all conversations."""
    conversations = get_all_conversations()
    return jsonify([dict(conv) for conv in conversations])


@app.route("/api/conversations/<conversation_id>/messages", methods=["GET"])
def get_messages(conversation_id):
    """Get all messages for a specific conversation."""
    messages = get_conversation_messages(conversation_id)
    return jsonify([dict(msg) for msg in messages])


@app.route("/api/conversations/<conversation_id>", methods=["DELETE"])
def delete_conv(conversation_id):
    """Delete a specific conversation."""
    delete_conversation(conversation_id)
    return jsonify({"status": "deleted", "conversation_id": conversation_id})


@app.route("/api/conversations/<conversation_id>/load", methods=["POST"])
def load_conversation(conversation_id):
    """Load a conversation into the session."""
    from database import get_conversation_messages, get_all_conversations

    # Check if conversation exists
    conversations = get_all_conversations()
    conv = next((dict(c) for c in conversations if c["id"] == conversation_id), None)

    if not conv:
        return jsonify({"error": "Conversation not found"}), 404

    # Get messages
    messages = get_conversation_messages(conversation_id)

    # Update session (only lightweight metadata, NOT history)
    session["conversation_id"] = conversation_id
    session["topic"] = conv["topic"]
    session["depth_level"] = conv["depth_level"]
    session["server_a_url"] = conv.get("server_a_url") or SERVER_A_URL
    session["server_b_url"] = conv.get("server_b_url") or SERVER_B_URL
    session["language"] = conv.get("language") or "en"
    session.modified = True

    # Build history for response (not stored in session to avoid cookie size limits)
    loaded_history = [
        {
            "role": msg["role"],
            "content": msg["content"],
            "sender": msg["sender"],
            "display": bool(msg["display"]),
        }
        for msg in messages
    ]

    system_prompt = get_depth_template(int(conv["depth_level"]), session["language"])
    if not any(h.get("role") == "system" for h in loaded_history):
        loaded_history.insert(0, {"role": "system", "content": system_prompt})

    return jsonify(
        {
            "status": "loaded",
            "topic": conv["topic"],
            "depth_level": conv["depth_level"],
            "server_a_url": conv.get("server_a_url"),
            "server_b_url": conv.get("server_b_url"),
            "language": session["language"],
            "history": loaded_history,
        }
    )


@app.route("/api/conversations", methods=["DELETE"])
def delete_all_conv():
    """Delete all conversations."""
    delete_all_conversations()
    return jsonify({"status": "all_deleted"})


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
