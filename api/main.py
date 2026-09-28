from fastapi import FastAPI
from api.routers import ingestion, auth, reorder

app = FastAPI(
    title="AI Workforce Orchestrator - Ingestion API",
    description="API for tenant onboarding and sale/order ingestion",
    version="0.1"
)

# Include routers
app.include_router(auth.router)
app.include_router(ingestion.router)
app.include_router(reorder.router)


@app.get("/dapr/subscribe")
async def dapr_subscriptions():
    return [
        {
            "pubsubname": "inventory-pubsub",
            "topic": "inventory-reorder",
            "route": "/reorder/events/inventory-reorder",
        }
    ]

@app.get("/")
async def root():
    return {"message": "AI Workforce Orchestrator Ingestion API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
