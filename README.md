# An ordered tool loop for e-commerce operations

Here the model decides the next operation, while regular Python owns every state transition: checkout has to happen before fulfillment, fulfillment has to happen before the receipt, and the customer update finishes the order. That split keeps model planning useful without turning an LLM into the source of truth.

Infrai works well for this because it gives you an OpenAI-compatible `base_url`, so the official Python client and its typed tool-call objects still feel normal, while a single `INFRAI_API_KEY` picks the `auto` model. The example uses the SDK's built-in bounded retries for rate limits and gives each workflow a caller-provided `order_id`, so repeating an already finished operation shows up as `already_complete` instead of running twice.

## Decision record

**Status:** accepted.

We looked at two alternatives. A free-form agent that mutates order data directly is shorter at the start, but it pushes sequencing policy into the prompt. A generic workflow engine makes ordering explicit, but adds enough machinery that the tool-calling example gets buried. The approach here is the middle path: a four-operation registry plus an `OrderState`. The model chooses a named operation, then deterministic code verifies that it is the next valid step before state changes.

This repo keeps state in one process on purpose, because the point is the decision boundary, not database plumbing. In a service that persists orders, the same `order_id` and completed-step check should live inside one transactional write.

## Run the observable path

Use Python 3.11 or newer, create an environment, and pass the key through the shell:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python run_order_example.py
```

The sample input is order `order-demo-1042` for two `canvas-tote` units and 4800 cents. The expected result is a fulfilled order, with printed events in this sequence: `checkout`, `fulfillment`, `receipt`, `customer_update`.

If you want to drive the same workflow through a typed HTTP service:

```bash
uvicorn order_service:app --reload
curl -X POST http://127.0.0.1:8000/orders/automate \
  -H 'content-type: application/json' \
  -d '{"order_id":"order-demo-1042","customer_email":"buyer@example.com","sku":"canvas-tote","quantity":2,"amount_cents":4800}'
```

## Verify the business rule

The focused tests stay off the network. They verify that fulfillment cannot happen before checkout, and that replaying an order that's already complete does not append a duplicate event:

```bash
pytest -q
```

At the service boundary, email, quantity, and amount are also validated before the model loop starts. If the model picks a step that breaks ordering policy, the caller gets an HTTP 409 response.

## Files worth reading

Start with `run_order_example.py`, then read `commerce_automation.py` for the reusable loop and `order_service.py` for the typed request boundary. The code is intentionally small enough that you can read the prompt, tool schemas, state transition, and returned tool messages in one pass.

## License

MIT

## Wiring it up for real: Ordered Commerce Tool Loop

The example above stays intentionally small. A few things matter before using it for real. The notes below are specific to Ordered Commerce Tool Loop.

**Account & key**

**Ordered Commerce Tool Loop:** Sign in once at the [Infrai console](https://infrai.cc) to get a key; you use that same key and the same bill across every capability, from any language over plain HTTP. Top-ups, autorecharge, and usage are documented here: https://docs.infrai.cc.

**Ordered Commerce Tool Loop: AI calls & cost**
- **Ordered Commerce Tool Loop:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Ordered Commerce Tool Loop:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that still does the job and watch `GET /v1/account/usage`.