import pytest

from commerce_automation import OrderRequest, OrderState, OrderTools, WorkflowError


def sample_order() -> OrderRequest:
    return OrderRequest("order-7", "buyer@example.com", "canvas-tote", 2, 4800)


def test_order_policy_requires_checkout_before_fulfillment() -> None:
    tools = OrderTools(OrderState(sample_order()))

    with pytest.raises(WorkflowError, match="expected checkout"):
        tools.execute("fulfillment")


def test_order_steps_are_ordered_and_replay_is_harmless() -> None:
    state = OrderState(sample_order())
    tools = OrderTools(state)

    for step in ("checkout", "fulfillment", "receipt", "customer_update"):
        assert tools.execute(step)["status"] == "completed"

    replay = tools.execute("customer_update")
    assert replay["status"] == "already_complete"
    assert state.completed == ["checkout", "fulfillment", "receipt", "customer_update"]
    assert len(state.events) == 4
