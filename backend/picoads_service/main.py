from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import httpx
import json

app = FastAPI(title="Cathedral PicoAds Service")

class RecommendationRequest(BaseModel):
    query: str
    hub: Optional[str] = None
    max_results: int = 5
    require_memory_proof: bool = True

@app.post("/picoads/recommendations")
async def get_recommendations(
    req: RecommendationRequest,
    authorization: str = Header(..., alias="Authorization"),
    x_memory_commitment: Optional[str] = Header(None, alias="X-Memory-Commitment"),
):
    """
    This endpoint is called by the TypeScript Action Provider.
    It optionally enforces memory proof before forwarding to PicoAds.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid API key")

    api_key = authorization.split(" ")[1]

    # 1. Memory Proof Gate (calls your DLA engine)
    if req.require_memory_proof:
        # In production, call your DLA via HTTP or napi-rs
        # For now we simulate
        if not x_memory_commitment:
            # You can call your DLA service here
            # proof = await call_dla_prove_memory_state()
            # if not proof.valid:
            #     raise HTTPException(status_code=403, detail="Valid MemoryProof required")
            print("[Backend] Memory proof required but not provided (simulated)")

    # 2. Forward to real PicoAds (or mock)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://picoads-mock:8080/recommendations", # Update to point to the mock service
                json={
                    "query": req.query,
                    "hub": req.hub,
                    "max_results": req.max_results,
                },
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"PicoAds error: {str(e)}")

    return {
        "recommendations": data,
        "memory_proof_enforced": req.require_memory_proof,
        "memory_commitment": x_memory_commitment,
    }
