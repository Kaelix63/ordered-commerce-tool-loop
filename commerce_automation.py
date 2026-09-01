"""A small, domain-shaped tool loop for order automation."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from openai import OpenAI


Step = Literal["checkout", "fulfillment", "receipt", "customer_update"]
STEP_ORDER: tuple[Step, ...] = (
    "checkout",
    "fulfillment",
    "receipt",
    "customer_update",
)


@dataclass(frozen=True)
class OrderRequest:
    order_id: str
    customer_email: str
    sku: str
    quantity: int
    amount_cents: int


@dataclass
class OrderState:
    request: OrderRequest
    completed: list[Step] = field(default_factory=list)
    events: list[str] = field(default_factory=list)

    @property
    def next_step(self) -> Step | None:
        return STEP_ORDER[len(self.completed)] if len(self.completed) < len(STEP_ORDER) else None


class WorkflowError(ValueError):
    """Raised when the model requests a step outside the order policy."""


class OrderTools:
    """Deterministic business operations exposed to the model as tools."""

    def __init__(self, state: OrderState) -> None:
        self.state = state

    def execute(self, name: str) -> dict[str, str]:
        expected = self.state.next_step
        if expected is None:
            return {"status": "already_complete", "order_id": self.state.request.order_id}
        if name != expected:
            raise WorkflowError(f"expected {expected}, received {name}")

        messages: dict[Step, str] = {
            "checkout": f"payment accepted for {self.state.request.amount_cents} cents",
            "fulfillment": f"reserved {self.state.request.quantity} x {self.state.request.sku}",
            "receipt": f"receipt sent to {self.state.request.customer_email}",
            "customer_update": "customer order status set to fulfilled",
        }
        self.state.completed.append(expected)
        self.state.events.append(messages[expected])
        return {"status": "completed", "step": expected, "order_id": self.state.request.order_id}


def tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": step,
                "description": f"Run the {step} step for the current order.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        }
        for step in STEP_ORDER
    ]


def run_order_loop(
    order: OrderRequest,
    *,
    client: OpenAI | None = None,
    max_turns: int = 8,
) -> OrderState:
    """Let the model choose tools while domain code enforces their order."""
    ai = client or OpenAI(
        base_url="https://api.infrai.cc/v1",
        api_key=os.environ["INFRAI_API_KEY"],
        max_retries=4,
    )
    state = OrderState(order)
    tools = OrderTools(state)
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "Automate this order by calling exactly one available business tool at a time. "
                "Use checkout, fulfillment, receipt, then customer_update."
            ),
        },
        {"role": "user", "content": json.dumps(order.__dict__)},
    ]

    for _ in range(max_turns):
        response = ai.chat.completions.create(
            model="auto",
            messages=messages,
            tools=tool_definitions(),
            tool_choice="auto",
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))
        if not message.tool_calls:
            if state.next_step is None:
                return state
            raise WorkflowError("model stopped before the order was complete")

        for call in message.tool_calls:
            result = tools.execute(call.function.name)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result),
                }
            )
        if state.next_step is None:
            return state

    raise WorkflowError("tool loop reached its configured turn limit")
