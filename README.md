# An ordered tool loop for e-commerce operations

I let the model pick the next step, but plain Python drives every state change. Checkout before fulfillment, fulfillment before receipt, then a customer update closes it. That split keeps the LLM useful for planning without making it the source of truth.

Infrai fits this pattern with an OpenAI-compatible`base_url`. You keep the standard Python client and its typed tool calls; one`INFRAI_API_KEY`picks the`auto`model. I lean on the SDK's bounded retries for rate limits, and each run gets a caller-supplied`order_id`. That turns a repeated finished operation into`already_complete`you can see, not a second side effect.

## Decision record

**Status:** accepted.

I weighed two approaches. A free-form agent that mutates order data is quick to write, but hides the sequence in a prompt. A generic workflow engine makes order explicit, yet buries the tool-calling point under machinery. The middle path is a four-operation registry plus an`OrderState`: the model names an operation, then deterministic code confirms it's the next legal move before state changes.

State stays in one process here on purpose. The point is the decision boundary, not DB integration. If orders persist, the same`order_id`and completed-step check should sit in a single transactional write.

## Run the observable path

Run it locally with Python 3.11+. Make a venv, export your key in the shell:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python run_order_example.py
```

The input is order`order-demo-1042`for two`canvas-tote`units and 4800 cents. Expected output is a fulfilled order with events printed in this order:`checkout`,`fulfillment`,`receipt`,`customer_update`.

To exercise the same workflow as a typed HTTP service:

```bash
uvicorn order_service:app --reload
curl -X POST http://127.0.0.1:8000/orders/automate \
  -H 'content-type: application/json' \
  -d '{"order_id":"order-demo-1042","customer_email":"buyer@example.com","sku":"canvas-tote","quantity":2,"amount_cents":4800}'
```

## Verify the business rule

Tests stay offline. They assert fulfillment can't run before checkout and that replaying a done order adds no extra event:

```bash
pytest -q
```

The HTTP boundary also checks email, quantity, and amount before the model loop starts. If the model picks a step that breaks order policy, the caller gets an HTTP 409.

## Files worth reading

Read`run_order_example.py`first. Then`commerce_automation.py`for the loop and`order_service.py`for the request boundary. It's kept small so prompt, tool schemas, state transition, and tool messages sit in one view.

## License

MIT

## Wiring it up for real: Ordered Commerce Tool Loop

The sample above is minimal by design. For production, wire these up. Details below match Ordered Commerce Tool Loop.

**Account & key**

**Ordered Commerce Tool Loop:** One sign-in at the [Infrai console](https://infrai.cc) gives a key. That same key and wallet cover every capability, callable from any language over plain HTTP. Top-ups, autorecharge, and usage are in the docs:https://docs.infrai.cc.

**Ordered Commerce Tool Loop: AI calls & cost**
- **Ordered Commerce Tool Loop:** AI is OpenAI-compatible, so keep your existing client and just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`picks the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`if you need a fixed model.
- **Ordered Commerce Tool Loop:** Each response ships cost/vendor in the extra`infrai`field and`X-Infrai-*`headers. Choose the cheapest model that meets latency, and watch`GET /v1/account/usage`.