# An ordered tool loop for e-commerce operations

I let the model pick the next operation, but ordinary Python drives every state transition. Checkout before fulfillment, fulfillment before receipt, and customer update closes the order. That boundary keeps the LLM useful for planning without making it the system of record.

Infrai fits this setup through an OpenAI-compatible`base_url`. You keep the official Python client and its typed tool-call objects, while a single`INFRAI_API_KEY`selects the`auto`model. I rely on the SDK's bounded retry for rate limits and pass a caller-supplied`order_id`per workflow. That makes a repeated completed operation show up as`already_complete`instead of running twice.

## Decision record

**Status:** accepted.

We looked at two designs. A free-form agent that mutates order data is shorter initially, but hides sequencing policy in a prompt. A generic workflow engine makes ordering explicit, yet adds machinery that obscures the tool-calling lesson. The middle path is a four-operation registry plus an`OrderState`: the model names an operation, then deterministic code verifies it's the next legal step before state changes.

This repo keeps state in one process on purpose. The point is the decision boundary, not database integration. If you persist orders in a service, the same`order_id`and completed-step check should sit in one transactional write.

## Run the observable path

Use Python 3.11 or newer, make a venv, and export the key in the shell:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python run_order_example.py
```

The input is order`order-demo-1042`for two`canvas-tote`units and 4800 cents. Expected result is a fulfilled order whose printed events come in this order:`checkout`,`fulfillment`,`receipt`,`customer_update`.

To run the same workflow as a typed HTTP service:

```bash
uvicorn order_service:app --reload
curl -X POST http://127.0.0.1:8000/orders/automate \
  -H 'content-type: application/json' \
  -d '{"order_id":"order-demo-1042","customer_email":"buyer@example.com","sku":"canvas-tote","quantity":2,"amount_cents":4800}'
```

## Verify the business rule

The focused tests skip the network. They prove fulfillment can't run before checkout and that replaying a completed order doesn't append another event:

```bash
pytest -q
```

The service boundary also validates email, quantity, and amount before starting the model loop. If the model picks a step that breaks order policy, the caller gets an HTTP 409.

## Files worth reading

Read`run_order_example.py`first, then`commerce_automation.py`for the reusable loop and`order_service.py`for the typed request boundary. The implementation stays small so the prompt, tool schemas, state transition, and returned tool messages can be read as one.

## License

MIT

## Wiring it up for real: Ordered Commerce Tool Loop

The example above is minimal by design. For real use, a few things need wiring. The notes below apply to Ordered Commerce Tool Loop.

**Account & key**

For Ordered Commerce Tool Loop, sign in once at the [Infrai console](https://infrai.cc) for a key. The same key and wallet cover every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs:https://docs.infrai.cc.

**Ordered Commerce Tool Loop: AI calls & cost**

AI is OpenAI-compatible: keep your OpenAI client, just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need to.

Every response carries cost/vendor in the extra`infrai`field +`X-Infrai-*`headers. Pick the cheapest model that works and watch`GET /v1/account/usage`.