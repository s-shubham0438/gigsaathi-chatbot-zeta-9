from app.schemas.chat import Intent
from app.services.intent import classify_intent


def test_greeting():
    assert classify_intent("Hello") == Intent.GREETING
    assert classify_intent("Hi") == Intent.GREETING


def test_service_problem_tap_leak():
    assert classify_intent("My tap is leaking") == Intent.SERVICE_PROBLEM


def test_service_problem_electrical_board():
    # Master prompt's own worked example (Section 9) labels this
    # SERVICE_PROBLEM / priority "Urgent" — not EMERGENCY_SERVICE (that's
    # reserved for an active safety risk like sparking/fire/shock).
    assert classify_intent("Electrical board fried ho gaya hai") == Intent.SERVICE_PROBLEM


def test_cancel_service():
    assert classify_intent("I want to cancel my booking") == Intent.CANCEL_SERVICE
    assert classify_intent("Meri booking cancel karni hai") == Intent.CANCEL_SERVICE


def test_worker_accept():
    assert classify_intent("I'll accept this request") == Intent.WORKER_ACCEPT_REQUEST


def test_dispute_report():
    assert classify_intent("Customer ke saath payment ko lekar dispute ho gaya hai") == Intent.DISPUTE_REPORT
    assert classify_intent("The worker was rude to me, I want to complain") == Intent.DISPUTE_REPORT


def test_price_estimation():
    assert classify_intent("Tap repair ke liye approx kitna lagega?") == Intent.PRICE_ESTIMATION


def test_support_contact():
    assert classify_intent("What is your helpline number?") == Intent.SUPPORT_CONTACT


def test_unknown_for_gibberish():
    assert classify_intent("asdkjhaskjdh") == Intent.UNKNOWN


def test_emergency_beats_service_problem():
    # "sparking" is both an electrical problem hint and an emergency marker —
    # emergency must win given the ordered rule list.
    assert classify_intent("My switchboard is sparking, please help urgently") == Intent.EMERGENCY_SERVICE
