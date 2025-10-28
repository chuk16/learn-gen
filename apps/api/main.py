from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import plan, assets, generate

app = FastAPI(title="Learn-Gen API", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

app.include_router(plan.router, prefix="/v1")
app.include_router(assets.router, prefix="/v1")
app.include_router(generate.router, prefix="/v1")
