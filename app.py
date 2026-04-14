from flask import Flask, render_template, request, jsonify, session
from logic import (
    run_single_turn,
    run_user_question,
    DEPTH_TEMPLATES,
    SERVER_A_URL,
    SERVER_B_URL,
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

app = Flask(__name__)
app.secret_key = "super_secret_key_for_session"  # In production, use a real secret key


@app.route("/")
def index():
    # Initialize a new session for a new conversation
    session["conversation_id"] = str(uuid.uuid4())
    session["history"] = []
    return render_template(
        "index.html", depth_templates=DEPTH_TEMPLATES, db_enabled=True
    )


@app.route("/start", methods=["POST"])
def start_conversation():
    data = request.json
    topic = data.get("topic")
    depth_level = int(data.get("depth_level", 2))

    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    # Initialize conversation_id if not exists
    if "conversation_id" not in session:
        session["conversation_id"] = str(uuid.uuid4())

    history = []
    # We use the session to store history
    session["history"] = history
    session["topic"] = topic
    session["depth_level"] = depth_level
    session.modified = True

    # Save conversation to database
    save_conversation(session["conversation_id"], topic, depth_level)

    return jsonify({"status": "started", "topic": topic})


@app.route("/next_turn", methods=["POST"])
def next_turn():
    history = session.get("history", [])
    topic = session.get("topic")
    depth_level = session.get("depth_level")

    if not topic:
        return jsonify({"error": "No active conversation"}), 400

    try:
        # Save old content count BEFORE calling run_single_turn (it modifies history in place)
        old_content_count = len(history)

        new_history, resp_a, resp_b = run_single_turn(topic, depth_level, history)

        # Save new messages to database
        for msg in new_history[old_content_count:]:
            save_message(
                session["conversation_id"],
                msg.get("role"),
                msg.get("content"),
                msg.get("sender"),
                msg.get("display", True),
            )

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

        # Save new messages to database
        old_content_count = len(history)
        for msg in new_history[old_content_count:]:
            save_message(
                session["conversation_id"],
                msg.get("role"),
                msg.get("content"),
                msg.get("sender"),
                msg.get("display", True),
            )

        session["history"] = new_history
        session.modified = True

        return jsonify(
            {"history": new_history, "response_a": resp_a, "response_b": resp_b}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
    conv = next((c for c in conversations if c["id"] == conversation_id), None)

    if not conv:
        return jsonify({"error": "Conversation not found"}), 404

    # Get messages
    messages = get_conversation_messages(conversation_id)

    # Update session
    session["conversation_id"] = conversation_id
    session["topic"] = conv["topic"]
    session["depth_level"] = conv["depth_level"]
    session["history"] = [
        {
            "role": msg["role"],
            "content": msg["content"],
            "sender": msg["sender"],
            "display": bool(msg["display"]),
        }
        for msg in messages
    ]
    session.modified = True

    return jsonify(
        {
            "status": "loaded",
            "topic": conv["topic"],
            "depth_level": conv["depth_level"],
            "history": session["history"],
        }
    )


@app.route("/api/conversations", methods=["DELETE"])
def delete_all_conv():
    """Delete all conversations."""
    delete_all_conversations()
    return jsonify({"status": "all_deleted"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
