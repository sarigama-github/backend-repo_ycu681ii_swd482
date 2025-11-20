"""
Database Schemas for Personal Finance Tracker

Each Pydantic model represents a collection in MongoDB. The collection
name is the lowercase of the class name (e.g., Transaction -> "transaction").
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class Account(BaseModel):
    name: str = Field(..., description="Account display name")
    type: Literal["checking", "savings", "credit", "investment", "cash"] = Field(
        ..., description="Account type"
    )
    institution: Optional[str] = Field(None, description="Bank or provider")
    last4: Optional[str] = Field(None, description="Last 4 digits if applicable")
    currency: str = Field("USD", description="Currency code")


class Transaction(BaseModel):
    date: datetime = Field(..., description="Transaction date")
    amount: float = Field(..., description="Positive for income, negative for expense")
    type: Literal["income", "expense"] = Field(..., description="Transaction type")
    category: str = Field(..., description="Category name, e.g., Groceries")
    account: str = Field(..., description="Account name or id")
    merchant: Optional[str] = Field(None, description="Merchant/payee")
    notes: Optional[str] = Field(None, description="Notes")
    currency: str = Field("USD", description="Currency code")


class Budget(BaseModel):
    month: str = Field(..., description="YYYY-MM for the budget month")
    category: str = Field(..., description="Budget category")
    amount: float = Field(..., ge=0, description="Budgeted amount for the month")

