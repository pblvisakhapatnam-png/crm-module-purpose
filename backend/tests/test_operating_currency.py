"""TB1-600: an amount may be recorded only in a currency on the one list (app/shared/currency.py).

The owner's decision of 4 October 2026: INR is the default; USD, GBP and EUR may be chosen; nothing else. Before it,
every currency field accepted any three letters ("XYZ"), and the reports added them all into one rupee total.

Every place a currency enters is tried here with a code off the list (refused, with the list in the message) and,
where a later step needs it, with one on the list (accepted).
"""

from __future__ import annotations

import pytest

from app.modules.commercial_offers.services import common as offer_service
from app.modules.commercial_offers.service import CommercialOfferValidationError
from app.modules.work_orders.services import amendments as amendment_service
from app.modules.work_orders.services.common import WorkOrderValidationError
from app.shared.currency import (
    DEFAULT_CURRENCY,
    OPERATING_CURRENCIES,
    UNSUPPORTED_CURRENCY_MESSAGE,
    operating_currency,
)
from tests.test_work_order_amendments_api import _build_accepted_work_order_chain, _teardown
from tests.test_commercial_offers_api import (
    auth_headers,
    client,
    create_test_offer_line,
    create_test_opportunity,
    mark_test_commercial_offer_submitted,
)
from tests.offer_version_test_support import line_row_version, offer_row_version

OFF_THE_LIST = "AUD"  # a real currency, deliberately not on the list


def test_the_list_is_inr_first_and_inr_is_the_default() -> None:
    assert OPERATING_CURRENCIES == ("INR", "USD", "GBP", "EUR")
    assert DEFAULT_CURRENCY == "INR"
    assert operating_currency(None) == "INR"
    assert operating_currency("") == "INR"
    assert operating_currency(" gbp ") == "GBP"
    for code in OPERATING_CURRENCIES:
        assert operating_currency(code) == code


@pytest.mark.parametrize("code", ["AUD", "XYZ", "IND", "IN", "RUPEE", "   "])
def test_a_code_off_the_list_is_refused(code: str) -> None:
    with pytest.raises(ValueError, match="Currency must be one of INR, USD, GBP, EUR."):
        operating_currency(code)


def test_each_module_refuses_with_its_own_error_and_the_one_message() -> None:
    with pytest.raises(CommercialOfferValidationError) as offer_error:
        offer_service._validate_currency("XYZ")
    with pytest.raises(WorkOrderValidationError) as amendment_error:
        amendment_service._validate_currency("XYZ")
    assert str(offer_error.value) == str(amendment_error.value) == UNSUPPORTED_CURRENCY_MESSAGE
    assert offer_service._validate_currency("usd") == amendment_service._validate_currency("usd") == "USD"


def _refused(response) -> None:
    assert response.status_code == 422, response.text
    assert UNSUPPORTED_CURRENCY_MESSAGE in response.text


def test_every_entry_point_refuses_a_currency_off_the_list() -> None:
    ids: dict[str, list[str]] = {
        "work_order_public_ids": [],
        "offer_public_ids": [],
        "opportunity_public_ids": [],
        "account_public_ids": [],
        "lead_public_ids": [],
    }
    headers = auth_headers("sales1")
    try:
        # A Work Order from an accepted offer: the offer, its line, its customer response and the Work Order exist.
        chain = _build_accepted_work_order_chain()
        ids["lead_public_ids"].append(str(chain["lead"]["public_id"]))
        ids["account_public_ids"].append(str(chain["account"]["public_id"]))
        ids["opportunity_public_ids"].append(str(chain["opportunity"]["public_id"]))
        base_offer = chain["base_offer_public_id"]
        ids["offer_public_ids"].append(base_offer)
        work_order = str(chain["work_order"]["public_id"])
        ids["work_order_public_ids"].append(work_order)

        # 1. A new offer, on an Opportunity of its own (the chain's already has its one live offer).
        opportunity = create_test_opportunity()
        ids["opportunity_public_ids"].append(str(opportunity["public_id"]))
        _refused(client.post(
            "/api/commercial-offers",
            headers=headers,
            json={"opportunity_public_id": opportunity["public_id"], "currency_code": OFF_THE_LIST},
        ))

        # 2. A related offer, from the accepted one.
        _refused(client.post(
            f"/api/commercial-offers/{base_offer}/related-offers",
            headers=headers,
            json={
                "offer_purpose": "SUPPLEMENTARY",
                "customer_request_summary": "Customer asked for one more crane.",
                "currency_code": OFF_THE_LIST,
            },
        ))
        related = client.post(
            f"/api/commercial-offers/{base_offer}/related-offers",
            headers=headers,
            json={
                "offer_purpose": "SUPPLEMENTARY",
                "customer_request_summary": "Customer asked for one more crane.",
                "currency_code": "usd",
            },
        )
        assert related.status_code == 201, related.text
        related_offer = related.json()["commercial_offer"]
        ids["offer_public_ids"].insert(0, str(related_offer["public_id"]))  # removed before the offer it came from
        assert related_offer["currency_code"] == "USD"
        related_public_id = str(related_offer["public_id"])

        # 3. Changing an offer's currency (the related offer is still a draft).
        _refused(client.put(
            f"/api/commercial-offers/{related_public_id}", headers=headers, json={"expected_row_version": offer_row_version(related_public_id), "currency_code": OFF_THE_LIST}
        ))
        changed = client.put(f"/api/commercial-offers/{related_public_id}", headers=headers, json={"expected_row_version": offer_row_version(related_public_id), "currency_code": "EUR"})
        assert changed.status_code == 200, changed.text
        assert changed.json()["commercial_offer"]["currency_code"] == "EUR"

        # 4 and 5. An offer line, added and changed.
        _refused(client.post(
            f"/api/commercial-offers/{related_public_id}/lines",
            headers=headers,
            json={"scope_description": "One more crane", "quantity": "1.00", "uom": "job", "currency_code": OFF_THE_LIST},
        ))
        line = create_test_offer_line(related_public_id)
        _refused(client.put(
            f"/api/commercial-offers/{related_public_id}/lines/{line['public_id']}",
            headers=headers,
            json={"expected_row_version": line_row_version(line['public_id']), "currency_code": OFF_THE_LIST},
        ))

        # 6. Pricing evidence.
        _refused(client.post(
            f"/api/commercial-offers/{related_public_id}/pricing-evidence",
            headers=headers,
            json={
                "line_public_id": line["public_id"],
                "evidence_type": "market_rate",
                "equipment_service_description": "80T crane day shift with operator",
                "rate_amount": "95000.00",
                "currency_code": OFF_THE_LIST,
                "rate_basis": "per_day",
            },
        ))

        # 7. The awarded currency on a customer response; the offer stays as it was.
        mark_test_commercial_offer_submitted(related_public_id)
        _refused(client.post(
            f"/api/commercial-offers/{related_public_id}/customer-responses",
            headers=headers,
            json={
                "response_outcome": "ACCEPTED_AWARDED",
                "response_received_at": "2026-07-13T11:00:00Z",
                "response_channel": "EMAIL",
                "awarded_amount_snapshot": "1000.00",
                "awarded_currency_snapshot": OFF_THE_LIST,
            },
        ))
        unchanged = client.get(f"/api/commercial-offers/{related_public_id}", headers=headers)
        assert unchanged.status_code == 200 and unchanged.json()["offer_status_code"] == "SUBMITTED"

        # 8 and 9. A Work Order amendment line, added and changed.
        amendment = client.post(
            f"/api/work-orders/{work_order}/amendments",
            headers=headers,
            json={
                "amendment_type_code": "COMMERCIAL",
                "received_date": "2026-07-13",
                "amendment_reason": "Customer requested one additional crane.",
                "commercial_change_summary": "Add one additional crane line.",
            },
        )
        assert amendment.status_code == 201, amendment.text
        lines_url = f"/api/work-orders/{work_order}/amendments/{amendment.json()['amendment']['public_id']}/lines"
        add_line = {
            "action_code": "ADD_LINE",
            "proposed_scope_description": "Provide one additional 80T crane with operator.",
            "proposed_rate_amount": "25000.00",
        }
        _refused(client.post(lines_url, headers=headers, json={**add_line, "proposed_currency_code": OFF_THE_LIST}))
        added = client.post(lines_url, headers=headers, json={**add_line, "proposed_currency_code": "GBP"})
        assert added.status_code == 201, added.text
        assert added.json()["amendment_line"]["proposed_currency_code"] == "GBP"
        _refused(client.put(
            f"{lines_url}/{added.json()['amendment_line']['public_id']}",
            headers=headers,
            json={"proposed_currency_code": OFF_THE_LIST},
        ))
    finally:
        _teardown(**ids)
