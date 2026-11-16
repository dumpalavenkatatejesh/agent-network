
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentResponse
from app.services.embeddings import generate_embedding

router = APIRouter(prefix="/api/v1/agents", tags=["Agents"])


@router.post(
    "/register",
    response_model=AgentResponse,
    status_code=201
)
def register_agent(
    payload: AgentCreate,
    db: Session = Depends(get_db)
):
    normalized_name = payload.company_name.strip().lower()
    webhook_url = str(payload.webhook_url).rstrip("/")

    # Prevent duplicate active registrations
    existing_agent = db.query(Agent).filter(
        Agent.is_active.is_(True),
        func.lower(Agent.company_name) == normalized_name,
        Agent.webhook_url == webhook_url
    ).first()

    if existing_agent:
        raise HTTPException(
            status_code=409,
            detail="An active agent with this company name and webhook URL already exists."
        )

    try:
        embedding = generate_embedding(payload.interest_manifesto)

        agent = Agent(
            company_name=payload.company_name.strip(),
            industry_category=payload.industry_category.strip(),
            webhook_url=webhook_url,
            interest_manifesto=payload.interest_manifesto.strip(),
            interest_embedding=embedding
        )

        db.add(agent)
        db.commit()
        db.refresh(agent)

        return agent

    except Exception:
        db.rollback()
        raise


@router.get("/", response_model=list[AgentResponse])
def get_agents(db: Session = Depends(get_db)):
    return (
        db.query(Agent)
        .filter(Agent.is_active.is_(True))
        .order_by(Agent.created_at.desc())
        .all()
    )


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: UUID, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()

    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent not found"
        )

    return agent
