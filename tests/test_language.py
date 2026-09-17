from app.services.language import detect_language


def test_english():
    assert detect_language("My kitchen tap is leaking.") == "english"


def test_hindi_devanagari():
    assert detect_language("मेरे किचन का नल लीक हो रहा है।") == "hindi"


def test_hinglish():
    assert detect_language("Mere ghar main kitchen ka tap leak ho raha hai.") == "hinglish"


def test_hinglish_short():
    assert detect_language("mera tap kharab hai") == "hinglish"


def test_empty_defaults_english():
    assert detect_language("") == "english"


def test_english_with_incidental_two_letter_overlap_not_flagged():
    # "ka" isn't a standalone English word, but make sure a normal English
    # sentence without real Hindi markers doesn't get misclassified.
    assert detect_language("Can you help me book a plumber for tomorrow?") == "english"
