"""Route a customer complaint to a support team.

The application owns the teams and their scopes. The model only scores which
scope fits the complaint best. The scope text does double duty: it guides the
model, and it is shown to the person as the reason for the routing.
"""

from __future__ import annotations

from .backends import Backend
from .decisions import Choice, Decision

TEAMS = {
    "returns": "Returns and exchanges: wrong size or colour, faulty or damaged items, swaps, "
               "return labels and the returns window.",
    "shipping": "Shipping and delivery: tracking, late or lost parcels, delivery addresses, "
                "couriers and international delivery.",
    "billing": "Billing and payments: charges, refunds to a card, invoices, discounts, VAT and currency.",
    "technical": "Website and app: login problems, error messages, crashes, and checkout or page bugs.",
}

QUESTION = Choice("Which support team should handle this complaint?", TEAMS)

# Below this, the application says the model is unsure and asks a person to
# look closely. The rule lives here, in code, not in a prompt.
UNSURE_BELOW = 0.3


def route(complaint: str, backend: Backend) -> Decision:
    return backend.decide(complaint, QUESTION)


def is_unsure(d: Decision) -> bool:
    return d.confidence < UNSURE_BELOW
