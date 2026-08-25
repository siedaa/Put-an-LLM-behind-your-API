from enum import Enum    # for restricted value sets

from pydantic import BaseModel, Field


class Category(str, Enum):
    billing = "billing"
    bug = "bug"
    feature = "feature"
    account = "account"
    other = "other"


class Urgency(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"


class SuggestedTeam(str, Enum):
    payments = "payments"
    engineering = "engineering"
    product = "product"
    support = "support"


class TriageRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class TriageResponse(BaseModel):
    category: Category
    urgency: Urgency
    suggested_team: SuggestedTeam
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(max_length=300)
