"""Run one order and print the observable workflow result."""

from commerce_automation import OrderRequest, run_order_loop


order = OrderRequest(
    order_id="order-demo-1042",
    customer_email="buyer@example.com",
    sku="canvas-tote",
    quantity=2,
    amount_cents=4800,
)
result = run_order_loop(order)

print(f"{result.request.order_id}: fulfilled")
for step, event in zip(result.completed, result.events, strict=True):
    print(f"- {step}: {event}")
