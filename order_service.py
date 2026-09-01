"""Typed HTTP boundary for the order automation workflow."""

from fastapi import FastAPI, HTTPException
from openai import APIStatusError
from pydantic import BaseModel, EmailStr, Field

from commerce_automation import OrderRequest, WorkflowError, run_order_loop


class AutomateOrderRequest(BaseModel):
    order_id: str = Field(min_length=1)
    customer_email: EmailStr
    sku: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    amount_cents: int = Field(gt=0)


class AutomateOrderResponse(BaseModel):
    order_id: str
    status: str
    completed_steps: list[str]
    events: list[str]


app = FastAPI(title="E-commerce tool loop")


@app.post("/orders/automate", response_model=AutomateOrderResponse)
def automate_order(body: AutomateOrderRequest) -> AutomateOrderResponse:
    try:
        state = run_order_loop(OrderRequest(**body.model_dump()))
    except WorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except APIStatusError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail="AI request was not accepted") from exc
    return AutomateOrderResponse(
        order_id=body.order_id,
        status="fulfilled",
        completed_steps=list(state.completed),
        events=state.events,
    )
