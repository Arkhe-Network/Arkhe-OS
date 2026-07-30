from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
import uuid

app = FastAPI(title="PicoAds Mock", description="Local test environment for PicoAds")

class RegisterRequest(BaseModel):
    name: str
    description: str

class RegisterResponse(BaseModel):
    api_key: str

class RecommendationRequest(BaseModel):
    query: str
    hub: Optional[str] = None
    max_results: Optional[int] = 5

class Recommendation(BaseModel):
    title: str
    description: str
    hub: str
    url: str
    estimated_value_usd: float

# In-memory storage
# Pre-register a dummy API key so the compose setup works out of the box
agents = {"pico_mock_api_key_here": {"name": "Test Agent", "description": "Mock description"}}

@app.post("/agents/register", response_model=RegisterResponse)
async def register_agent(req: RegisterRequest):
    api_key = f"pico_mock_{uuid.uuid4().hex[:16]}"
    agents[api_key] = {"name": req.name, "description": req.description}
    return RegisterResponse(api_key=api_key)

@app.post("/recommendations", response_model=List[Recommendation])
async def get_recommendations(
    req: RecommendationRequest,
    authorization: str = Header(..., alias="Authorization"),
    x_memory_commitment: Optional[str] = Header(None, alias="X-Memory-Commitment"),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth")
    api_key = authorization.split(" ")[1]
    if api_key not in agents:
        raise HTTPException(status_code=403, detail="Unknown agent")

    # Log memory commitment if provided
    if x_memory_commitment:
        print(f"[MemoryCommitment] {x_memory_commitment[:16]}...")

    # Return dummy recommendations
    return [
        Recommendation(
            title="Aave V3 Yield Vault",
            description="8% APY on USDC, auto-compounding",
            hub="defi-yield",
            url="https://app.aave.com/?ref=picoads",
            estimated_value_usd=12.50,
        ),
        Recommendation(
            title="Superchain DeFi Dashboard",
            description="Track LP positions across 10 chains",
            hub="defi-yield",
            url="https://debank.com/?ref=picoads",
            estimated_value_usd=8.20,
        ),
    ]
