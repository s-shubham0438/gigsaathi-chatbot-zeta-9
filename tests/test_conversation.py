from app.services.conversation import ConversationStore
from app.config import settings


def test_new_conversation_gets_new_id():
    store = ConversationStore()
    state = store.get_or_create(None, user_id="u1")
    assert state.conversation_id
    assert state.user_id == "u1"


def test_reusing_conversation_id_returns_same_state():
    store = ConversationStore()
    state1 = store.get_or_create(None, user_id="u1")
    state1.category = "plumbing"
    state2 = store.get_or_create(state1.conversation_id, user_id="u1")
    assert state2.category == "plumbing"
    assert state1 is state2


def test_cross_user_access_does_not_leak_state():
    store = ConversationStore()
    state1 = store.get_or_create(None, user_id="u1")
    state1.category = "plumbing"
    # u2 tries to reuse u1's conversation id — must get a fresh conversation.
    state2 = store.get_or_create(state1.conversation_id, user_id="u2")
    assert state2.category is None
    assert state2.user_id == "u2"


def test_turns_are_capped_at_configured_max():
    store = ConversationStore()
    state = store.get_or_create(None, user_id="u1")
    for i in range(settings.conversation_max_turns + 10):
        state.add_turn("user", f"message {i}")
    assert len(state.recent_history()) == settings.conversation_max_turns
    # Oldest turns are the ones dropped, newest retained.
    assert state.recent_history()[-1].text == f"message {settings.conversation_max_turns + 9}"
