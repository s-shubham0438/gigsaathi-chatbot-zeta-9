from app.services.category import classify_category

LIVE_CATEGORIES = ["plumbing", "electrical", "cleaning", "appliance", "carpentry", "painting"]


def test_tap_leak_is_plumbing():
    result = classify_category("My tap is leaking", LIVE_CATEGORIES)
    assert result.category == "plumbing"
    assert result.priority == "normal"


def test_electrical_board_fried_is_electrical_and_urgent():
    # Matches the master prompt's own worked example (Section 9): priority
    # "Urgent", not "Emergency" (no active safety risk stated).
    result = classify_category("Electrical board fried ho gaya hai", LIVE_CATEGORIES)
    assert result.category == "electrical"
    assert result.priority == "urgent"


def test_sparking_switchboard_is_emergency():
    result = classify_category("My switchboard is sparking, please help", LIVE_CATEGORIES)
    assert result.category == "electrical"
    assert result.priority == "emergency"


def test_hinglish_kitchen_tap_leak():
    result = classify_category("Mere ghar main kitchen ka tap leak ho raha hai.", LIVE_CATEGORIES)
    assert result.category == "plumbing"


def test_urgent_marker():
    result = classify_category("AC is not cooling, need it fixed jaldi", LIVE_CATEGORIES)
    assert result.category == "appliance"
    assert result.priority == "urgent"


def test_no_match_returns_none_category():
    result = classify_category("What is the weather today", LIVE_CATEGORIES)
    assert result.category is None


def test_only_offers_categories_actually_live():
    # "gardening" has no live Service documents (see AI_CONTEXT.md section I)
    # so it must never be matched even if a future keyword list added it.
    result = classify_category("I need someone to mow my lawn", live_categories=["plumbing", "electrical"])
    assert result.category is None
