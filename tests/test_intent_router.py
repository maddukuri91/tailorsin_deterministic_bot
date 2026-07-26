from conversation.intent_router import get_intent
from conversation.menu import get_menu_options


def test_direct_menu_number_match():
    client_type = "client"
    assert get_intent(client_type, "1") == "new_order"
    assert get_intent(client_type, "8") == "address_update"


def test_menu_label_match_case_insensitive():
    client_type = "active_client"
    assert get_intent(client_type, "Track my current order") == "order_status"
    assert get_intent(client_type, "1. Track my current order") == "order_status"


def test_footer_intent():
    assert get_intent("client", "9") == "handover"
    assert get_intent("client", "0") == "main_menu"


def test_visit_history_special_input():
    assert get_intent("client", "visit history") == "visit_history"
    assert get_intent("client", "my appointments") == "visit_history"


def test_unknown_returns_none():
    assert get_intent("client", "banana") is None


def test_all_menu_options_resolve_to_known_intents():
    for client_type in ["active_client", "client", "new_user"]:
        menu = get_menu_options(client_type)
        for index, item in enumerate(menu, start=1):
            assert get_intent(client_type, str(index)) == item["intent"]
