#!/usr/bin/env python3
"""
Test script to verify conversation history is saved and retrieved correctly.
"""

from database import (
    init_db,
    save_conversation,
    save_message,
    get_all_conversations,
    get_conversation_messages,
    delete_conversation,
    delete_all_conversations,
)
import uuid


def test_basic_operations():
    """Test basic database operations."""
    print("=== Testing Basic Database Operations ===\n")

    # Clear database
    delete_all_conversations()
    print("✓ Database cleared\n")

    # Create a test conversation
    conv_id = str(uuid.uuid4())
    topic = "Test conversatie"
    depth_level = 2

    save_conversation(conv_id, topic, depth_level)
    print(f"✓ Created conversation: {topic}")

    # Save some test messages
    test_messages = [
        {"role": "user", "content": "Hallo, hoe gaat het?", "display": True},
        {
            "role": "assistant",
            "content": "Het gaat goed, dank je!",
            "sender": "Server A",
            "display": True,
        },
        {"role": "user", "content": "Interessant...", "display": False},
        {
            "role": "assistant",
            "content": "Ja, het is zeker interessant.",
            "sender": "Server B",
            "display": True,
        },
    ]

    for msg in test_messages:
        save_message(
            conv_id,
            msg["role"],
            msg["content"],
            msg.get("sender"),
            msg.get("display", True),
        )

    print(f"✓ Saved {len(test_messages)} messages\n")

    # Retrieve conversations
    conversations = get_all_conversations()
    print(f"✓ Retrieved {len(conversations)} conversation(s)")

    assert len(conversations) == 1, "Should have 1 conversation"
    assert conversations[0]["topic"] == topic, "Topic should match"
    print("✓ Conversation data verified\n")

    # Retrieve messages
    messages = get_conversation_messages(conv_id)
    print(f"✓ Retrieved {len(messages)} messages")

    assert len(messages) == len(test_messages), "Should have same number of messages"

    # Check displayed messages only
    displayed_messages = [m for m in messages if m["display"] == 1]
    print(
        f"✓ Found {len(displayed_messages)} displayed messages (out of {len(messages)} total)\n"
    )

    # Print message content
    print("Messages:")
    for i, msg in enumerate(messages, 1):
        display_status = "✓" if msg["display"] else "✗"
        sender = msg["sender"] or "-"
        print(
            f"  {i}. [{display_status}] {msg['role']:10} | {sender:10} | {msg['content'][:40]}..."
        )
    print()

    # Test delete single conversation
    delete_conversation(conv_id)
    print("✓ Deleted conversation")

    conversations = get_all_conversations()
    assert len(conversations) == 0, "Should have 0 conversations after delete"
    print("✓ Deletion verified\n")

    print("=== All tests passed! ===\n")


def test_multiple_conversations():
    """Test multiple conversations."""
    print("=== Testing Multiple Conversations ===\n")

    delete_all_conversations()

    # Create multiple conversations
    topics = ["AI toekomst", "Klimaatverandering", "Ruimteverkenning"]
    conv_ids = []

    for topic in topics:
        conv_id = str(uuid.uuid4())
        save_conversation(conv_id, topic, 2)
        conv_ids.append((conv_id, topic))

        # Add some messages
        save_message(conv_id, "user", f"Vraag over {topic}", display=True)
        save_message(
            conv_id, "assistant", f"Antwoord over {topic}", "Server A", display=True
        )
        print(f"✓ Created conversation: {topic}")

    print()

    # Retrieve all
    conversations = get_all_conversations()
    print(f"✓ Retrieved {len(conversations)} conversations\n")

    assert len(conversations) == len(topics), "Should have same number of conversations"

    # List all conversations
    print("All conversations:")
    for conv in conversations:
        msgs = get_conversation_messages(conv["id"])
        print(f"  - {conv['topic']}: {len(msgs)} messages")
    print()

    # Delete all
    delete_all_conversations()
    print("✓ Deleted all conversations\n")

    print("=== Multiple conversation test passed! ===\n")


if __name__ == "__main__":
    # Initialize database
    init_db()
    print("Database initialized\n")
    print("=" * 50)
    print()

    try:
        test_basic_operations()
        print()
        test_multiple_conversations()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
