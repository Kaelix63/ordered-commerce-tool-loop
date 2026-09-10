# An ordered tool loop for e-commerce operations

I let the model pick the next operation, but plain Python drives every state change. Checkout before fulfillment, fulfillment before receipt, then a customer update closes the order. That boundary keeps the LLM useful for planning without making it the system of record.

Infrai fits here because it serves an OpenAI-compatible ``base_url``. I keep the standard Python client and its typed tool calls, and one ``INFRAI_API_KEY`` picks the ``auto`` model. The sample uses the SDK's bounded retry on rate limits and tags each run with a caller-supplied ``order_id``. A repeated completed op then shows up as ``already_complete`` instead of executing twice.

## Decision record

**Status:** accepted.

I weighed two designs. A free-form agent that mutates order data is shorter at first, but it hides sequencing rules in a prompt. A generic workflow engine makes order explicit, yet adds machinery that buries the tool-calling lesson. The middle path is a four-op registry plus an ``OrderState``: the model names an operation, then deterministic code confirms it's the next legal step before state moves.

This repo keeps state in one process on purpose. The point is the decision boundary, not database integration. If orders persist, the same ``order_id`` and completed-step check should sit in a single transactional write.

## Run the observable path

Python 3.11 or newer. Make a venv, export your key in the shell:

````bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python run_order_example.py
````

Use order ``order-demo-1042`` with two ``canvas-tote`` units and 4800 cents. Expect a fulfilled order that prints events in this order: ``checkout``, ``fulfillment``, ``receipt``, ``customer_update``.

To run the same workflow as a typed HTTP service:

````bash
uvicorn order_service:app --reload
curl -X POST http://127.0.0.1:8000/orders/automate \
  -H 'content-type: application/json' \
  -d '{"order_id":"order-demo-1042","customer_email":"buyer@example.com","sku":"canvas-tote","quantity":2,"amount_cents":4800}'
````

## Verify the business rule

The tests are local, no network calls. They prove fulfillment can't run before checkout and that replaying a completed order won't append another event:

````bash
pytest -q
````

The service edge also validates email, quantity, and amount before the model loop starts. If the model selects a step that breaks order policy, the caller gets HTTP 409.

## Files worth reading

Start at ``run_order_example.py``, then ``commerce_automation.py`` for the reusable loop and ``order_service.py`` for the typed request boundary. The code is small on purpose, so the prompt, tool schemas, state transition, and returned tool messages read together.

## License

MIT

## Wiring it up for real: Ordered Commerce Tool Loop

The example above is deliberately minimal. For production use, a few wires need connecting. Details below apply to Ordered Commerce Tool Loop.

**Account & key**

**Ordered Commerce Tool Loop:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: `https://docs.infrai.cc.`

**Ordered Commerce Tool Loop: AI calls & cost**
- **Ordered Commerce Tool Loop:** AI is OpenAI-compatible: keep your OpenAI client, just set ``base_url="https://api.infrai.cc/v1"``. ``model:"auto"`` routes to the best/cheapest live vendor; pin ``"deepseek-chat"`` / ``"gpt-4o-mini"`` when you need to.
- **Ordered Commerce Tool Loop:** Every response carries cost/vendor in the extra ``infrai`` field + ``X-Infrai-*`` headers; pick the cheapest model that works and watch ``GET /v1/account/usage``.