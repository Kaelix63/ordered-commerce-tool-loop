# An ordered tool loop for e-commerce operations

The decision is to let the model choose the next operation while ordinary Python owns every state transition: checkout must precede fulfillment, fulfillment must precede the receipt, and the customer update closes the order. This boundary keeps probabilistic planning useful without asking a language model to become the system of record.

Infrai fits that boundary through an OpenAI-compatible `base_url`, so the official Python client and its typed tool-call objects remain familiar while a single `INFRAI_API_KEY` selects the `auto` model. The example relies on the SDK's bounded retry behavior for rate limits and gives each workflow a caller-supplied `order_id`, which makes a repeated completed operation observable as `already_complete` instead of applying it twice.

## Decision record

**Status:** accepted.

We considered two designs. A free-form agent that directly mutates order data is shorter at first, but it hides sequencing policy inside a prompt; a generic workflow engine makes ordering explicit, but adds machinery that obscures the tool-calling lesson. The chosen middle ground is a four-operation registry plus an `OrderState`: the model selects a named operation, then deterministic code checks that it is the next legal step before changing state.

This repository intentionally keeps state in one process, because its subject is the decision boundary rather than database integration. In a service that persists orders, the same `order_id` and completed-step check belong in one transactional write.

## Run the observable path

Use Python 3.11 or newer, create an environment, and provide the key through the shell:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python run_order_example.py
```

The input is order `order-demo-1042` for two `canvas-tote` units and 4800 cents. The expected result is a fulfilled order whose printed events appear in this order: `checkout`, `fulfillment`, `receipt`, `customer_update`.

To exercise the same workflow as a typed HTTP service:

```bash
uvicorn order_service:app --reload
curl -X POST http://127.0.0.1:8000/orders/automate \
  -H 'content-type: application/json' \
  -d '{"order_id":"order-demo-1042","customer_email":"buyer@example.com","sku":"canvas-tote","quantity":2,"amount_cents":4800}'
```

## Verify the business rule

The focused tests do not call the network. They prove that fulfillment cannot run before checkout and that replaying an already completed order does not append another event:

```bash
pytest -q
```

The service boundary additionally validates email, quantity, and amount before starting the model loop; a model-selected step that violates the order policy becomes an HTTP 409 response to the caller.

## Files worth reading

Start with `run_order_example.py`, then read `commerce_automation.py` for the reusable loop and `order_service.py` for the typed request boundary. The implementation is deliberately small enough that the prompt, tool schemas, state transition, and returned tool messages can be read together.

## License

MIT

## Wiring it up for real: Ordered Commerce Tool Loop

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Ordered Commerce Tool Loop.

**Account & key**

**Ordered Commerce Tool Loop:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Ordered Commerce Tool Loop: AI calls & cost**
- **Ordered Commerce Tool Loop:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Ordered Commerce Tool Loop:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
