import os
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Transaction, Account, Budget

app = FastAPI(title="Personal Finance API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, "name") else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# -------- Finance Endpoints -------- #

class TransactionIn(BaseModel):
    date: datetime
    amount: float
    type: str
    category: str
    account: str
    merchant: Optional[str] = None
    notes: Optional[str] = None
    currency: str = "USD"


@app.get("/api/transactions")
def list_transactions(limit: int = 20) -> List[Dict[str, Any]]:
    try:
        docs = get_documents("transaction", {}, limit)
        # Sort latest first by date or created_at
        def sort_key(d):
            return d.get("date") or d.get("created_at") or datetime(1970, 1, 1, tzinfo=timezone.utc)
        docs = sorted(docs, key=sort_key, reverse=True)
        # Convert ObjectId and datetimes to iso strings
        for d in docs:
            if "_id" in d:
                d["id"] = str(d.pop("_id"))
            for k, v in list(d.items()):
                if isinstance(v, datetime):
                    d[k] = v.isoformat()
        return docs
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.post("/api/transactions", status_code=201)
def create_transaction(payload: TransactionIn):
    try:
        # Validate against schema
        tx = Transaction(**payload.model_dump())
        inserted_id = create_document("transaction", tx)
        return {"id": inserted_id, "status": "created"}
    except Exception as e:
        raise HTTPException(400, detail=str(e))


@app.get("/api/summary")
def get_summary():
    """Compute simple MTD summary and category breakdown"""
    try:
        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        docs = get_documents("transaction", {"date": {"$gte": month_start}}, None)
        income = 0.0
        expense = 0.0
        by_category: Dict[str, float] = {}

        for d in docs:
            amt = float(d.get("amount", 0))
            ttype = d.get("type", "expense")
            cat = d.get("category", "Other")
            if ttype == "income":
                income += amt
                by_category.setdefault("Income", 0.0)
                by_category["Income"] += amt
            else:
                # treat expenses as positive values in breakdown
                expense += abs(amt)
                by_category.setdefault(cat, 0.0)
                by_category[cat] += abs(amt)

        net = income - expense
        # Convert to list for consistent ordering
        categories = [
            {"name": k, "amount": round(v, 2)} for k, v in sorted(by_category.items(), key=lambda x: x[1], reverse=True)
        ]
        return {
            "month": now.strftime("%Y-%m"),
            "income": round(income, 2),
            "expense": round(expense, 2),
            "net": round(net, 2),
            "categories": categories,
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# Optional demo seeding endpoint for quick visuals
@app.post("/api/demo/seed")
def seed_demo():
    try:
        sample: List[TransactionIn] = [
            TransactionIn(date=datetime.now(timezone.utc), amount=-54.23, type="expense", category="Groceries", account="Checking", merchant="Wholefoods"),
            TransactionIn(date=datetime.now(timezone.utc), amount=-18.5, type="expense", category="Transport", account="Checking", merchant="Uber"),
            TransactionIn(date=datetime.now(timezone.utc), amount=2500.0, type="income", category="Salary", account="Checking", merchant="Acme Inc"),
            TransactionIn(date=datetime.now(timezone.utc), amount=-89.99, type="expense", category="Shopping", account="Credit", merchant="Uniqlo"),
            TransactionIn(date=datetime.now(timezone.utc), amount=-12.99, type="expense", category="Subscriptions", account="Credit", merchant="Spotify"),
        ]
        for tx in sample:
            create_document("transaction", Transaction(**tx.model_dump()))
        return {"status": "ok", "inserted": len(sample)}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
