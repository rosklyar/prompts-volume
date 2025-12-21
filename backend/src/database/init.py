"""Database initialization and seeding logic."""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    AIAssistant,
    AIAssistantPlan,
    BusinessDomain,
    Country,
    CountryLanguage,
    EvaluationStatus,
    Language,
    Prompt,
    PromptEvaluation,
    Topic,
)
from src.embeddings.embeddings_service import get_embeddings_service


async def seed_initial_data(session: AsyncSession) -> None:
    """
    Seed initial data into the database.
    This function is idempotent - it will only insert data if it doesn't exist.

    Args:
        session: AsyncSession to use for database operations
    """
    # 1. Seed Languages
    await _seed_languages(session)

    # 2. Seed Countries
    await _seed_countries(session)

    # 3. Seed Country-Language mappings
    await _seed_country_languages(session)

    # 4. Seed Business Domains
    await _seed_business_domains(session)

    # 5. Seed Topics (requires countries and business domains)
    await _seed_topics(session)

    # 6. Seed Prompts (requires topics)
    await _seed_prompts(session)

    # 7. Seed AI Assistants
    await _seed_ai_assistants(session)

    # 8. Seed AI Assistant Plans (requires assistants)
    await _seed_ai_assistant_plans(session)

    # 9. Seed Phone Evaluations (requires prompts and assistant plans)
    await _seed_phone_evaluations(session)

    # 10. Seed Laptop Evaluations (requires prompts and assistant plans)
    await _seed_laptop_evaluations(session)

    await session.commit()


async def _seed_languages(session: AsyncSession) -> None:
    """Seed initial languages (Ukrainian, Russian, English)."""
    # Check if languages already exist
    result = await session.execute(select(Language).where(Language.id.in_([1, 2, 3])))
    existing_languages = result.scalars().all()

    if len(existing_languages) == 0:
        languages = [
            Language(id=1, name="Ukrainian", code="uk"),
            Language(id=2, name="Russian", code="ru"),
            Language(id=3, name="English", code="en"),
        ]
        session.add_all(languages)
        await session.flush()

        # Reset sequence to continue from the highest ID
        await session.execute(
            text("SELECT setval('languages_id_seq', (SELECT MAX(id) FROM languages))")
        )


async def _seed_countries(session: AsyncSession) -> None:
    """Seed initial countries."""
    # Check if Ukraine already exists
    result = await session.execute(select(Country).where(Country.iso_code == "UA"))
    existing = result.scalar_one_or_none()

    if existing is None:
        ukraine = Country(
            id=1,
            name="Ukraine",
            iso_code="UA",
        )
        session.add(ukraine)
        await session.flush()

        # Reset sequence to continue from the highest ID
        await session.execute(
            text("SELECT setval('countries_id_seq', (SELECT MAX(id) FROM countries))")
        )


async def _seed_country_languages(session: AsyncSession) -> None:
    """Seed country-language mappings (Ukraine -> Ukrainian, Russian)."""
    # Check if mappings already exist
    result = await session.execute(
        select(CountryLanguage).where(CountryLanguage.country_id == 1)
    )
    existing_mappings = result.scalars().all()

    if len(existing_mappings) == 0:
        mappings = [
            CountryLanguage(country_id=1, language_id=1, order=0),  # Ukraine -> Ukrainian (primary)
            CountryLanguage(country_id=1, language_id=2, order=1),  # Ukraine -> Russian (secondary)
        ]
        session.add_all(mappings)
        await session.flush()


async def _seed_business_domains(session: AsyncSession) -> None:
    """Seed initial business domains."""
    # Check if E_COMMERCE already exists
    result = await session.execute(
        select(BusinessDomain).where(BusinessDomain.name == "e-comm")
    )
    existing = result.scalar_one_or_none()

    if existing is None:
        e_commerce = BusinessDomain(
            id=1,
            name="e-comm",
            description="E-commerce is the buying and selling of goods and services over the internet",
        )
        session.add(e_commerce)
        await session.flush()

        # Reset sequence to continue from the highest ID
        await session.execute(
            text(
                "SELECT setval('business_domains_id_seq', (SELECT MAX(id) FROM business_domains))"
            )
        )


async def _seed_topics(session: AsyncSession) -> None:
    """Seed initial topics for Ukrainian e-commerce."""
    # Check if topics already exist
    result = await session.execute(select(Topic).where(Topic.id.in_([1, 2])))
    existing_topics = result.scalars().all()

    if len(existing_topics) == 0:
        # Topic 1: Smartphones and phones
        topic1 = Topic(
            id=1,
            title="Смартфони і телефони",
            description="Пошук і покупка телефонів і смартфонів в інтернеті",
            business_domain_id=1,
            country_id=1,
        )

        # Topic 2: Laptops and PCs
        topic2 = Topic(
            id=2,
            title="Ноутбуки та персональні комп'ютери",
            description="Пошук і покупка ноутбуків та персональні комп'ютерів в інтернеті",
            business_domain_id=1,
            country_id=1,
        )

        session.add_all([topic1, topic2])
        await session.flush()

        # Reset sequence to continue from the highest ID
        await session.execute(
            text("SELECT setval('topics_id_seq', (SELECT MAX(id) FROM topics))")
        )


async def _seed_prompts(session: AsyncSession) -> None:
    """
    Seed prompts from CSV files with embeddings.

    Loads prompts from:
    - prompts_phones.csv -> topic_id=1 (Смартфони і телефони)
    - prompts_laptops.csv -> topic_id=2 (Ноутбуки та персональні комп'ютери)
    """
    # Check if prompts already exist
    result = await session.execute(select(Prompt).limit(1))
    existing_prompt = result.scalar_one_or_none()

    if existing_prompt is not None:
        # Prompts already seeded, skip
        return

    # Get embeddings service
    embeddings_service = get_embeddings_service()

    # Base path for CSV files (src/data directory)
    data_dir = Path(__file__).parent.parent / "data"

    # Define CSV files and their corresponding topic IDs
    csv_files = [
        (data_dir / "prompts_phones.csv", 1),    # Smartphones
        (data_dir / "prompts_laptops.csv", 2),   # Laptops
    ]

    all_prompts = []

    for csv_path, topic_id in csv_files:
        if not csv_path.exists():
            continue

        # Read prompts from CSV
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            prompt_texts = [row["prompt"] for row in reader]

        if not prompt_texts:
            continue

        # Generate embeddings in batch for all prompts of this topic
        text_embeddings = embeddings_service.encode_texts(
            prompt_texts,
            batch_size=64,
            show_progress=False
        )

        # Create Prompt objects
        for te in text_embeddings:
            prompt = Prompt(
                prompt_text=te.text,
                embedding=te.embedding.tolist(),
                topic_id=topic_id,
            )
            all_prompts.append(prompt)

    # Bulk insert all prompts
    if all_prompts:
        session.add_all(all_prompts)
        await session.flush()


async def _seed_ai_assistants(session: AsyncSession) -> None:
    """Seed initial AI assistants."""
    # Check if ChatGPT already exists
    result = await session.execute(
        select(AIAssistant).where(AIAssistant.name == "ChatGPT")
    )
    existing = result.scalar_one_or_none()

    if existing is None:
        chatgpt = AIAssistant(
            id=1,
            name="ChatGPT",
        )
        session.add(chatgpt)
        await session.flush()

        # Reset sequence to continue from the highest ID
        await session.execute(
            text("SELECT setval('ai_assistants_id_seq', (SELECT MAX(id) FROM ai_assistants))")
        )


async def _seed_ai_assistant_plans(session: AsyncSession) -> None:
    """Seed initial AI assistant plans."""
    # Check if plans already exist for ChatGPT (assistant_id=1)
    result = await session.execute(
        select(AIAssistantPlan).where(AIAssistantPlan.assistant_id == 1)
    )
    existing_plans = result.scalars().all()

    if len(existing_plans) == 0:
        plans = [
            AIAssistantPlan(id=1, assistant_id=1, name="FREE"),
            AIAssistantPlan(id=2, assistant_id=1, name="PLUS"),
            AIAssistantPlan(id=3, assistant_id=1, name="PRO"),
        ]
        session.add_all(plans)
        await session.flush()

        # Reset sequence to continue from the highest ID
        await session.execute(
            text("SELECT setval('ai_assistant_plans_id_seq', (SELECT MAX(id) FROM ai_assistant_plans))")
        )


async def _seed_phone_evaluations(session: AsyncSession) -> None:
    """Seed phone prompt evaluations from JSON data."""
    # 1. Idempotency check
    result = await session.execute(
        select(PromptEvaluation)
        .join(Prompt)
        .where(
            Prompt.topic_id == 1,
            PromptEvaluation.assistant_plan_id == 1,
        )
        .limit(1)
    )
    if result.scalar_one_or_none() is not None:
        return  # Already seeded

    # 2. Load JSON data
    json_path = Path(__file__).parent.parent / "data" / "results" / "phones.json"
    with open(json_path, "r", encoding="utf-8") as f:
        phones_data = json.load(f)

    # 3. Get prompts from database (ordered by ID for consistent mapping)
    result = await session.execute(
        select(Prompt)
        .where(Prompt.topic_id == 1)
        .order_by(Prompt.id.asc())
    )
    prompts = result.scalars().all()

    # 4. Build evaluations
    evaluations = []
    for idx, phone_data in enumerate(phones_data):
        if idx >= len(prompts):
            break  # Safety check

        prompt = prompts[idx]
        answers = phone_data.get("answers", [])
        if not answers:
            continue  # Skip if no answers

        # Use first answer
        answer = answers[0]

        # Skip if timestamp is missing
        if "timestamp" not in answer:
            continue

        # Parse timestamp and calculate dates
        completed_at = datetime.fromisoformat(answer["timestamp"])
        claimed_at = completed_at - timedelta(hours=1)
        created_at = completed_at - timedelta(hours=2)

        # Build answer JSON
        answer_json = {
            "response": answer["response"],
            "citations": answer["citations"],
            "timestamp": answer["timestamp"]
        }

        # Create evaluation
        evaluation = PromptEvaluation(
            prompt_id=prompt.id,
            assistant_plan_id=1,  # ChatGPT Free
            status=EvaluationStatus.COMPLETED,
            answer=answer_json,
            created_at=created_at,
            claimed_at=claimed_at,
            completed_at=completed_at,
        )
        evaluations.append(evaluation)

    # 5. Bulk insert
    if evaluations:
        session.add_all(evaluations)
        await session.flush()

        # 6. Reset sequence
        await session.execute(
            text(
                "SELECT setval('prompt_evaluations_id_seq', "
                "(SELECT MAX(id) FROM prompt_evaluations))"
            )
        )


async def _seed_laptop_evaluations(session: AsyncSession) -> None:
    """Seed laptop prompt evaluations from JSON data."""
    # 1. Idempotency check
    result = await session.execute(
        select(PromptEvaluation)
        .join(Prompt)
        .where(
            Prompt.topic_id == 2,
            PromptEvaluation.assistant_plan_id == 1,
        )
        .limit(1)
    )
    if result.scalar_one_or_none() is not None:
        return  # Already seeded

    # 2. Load JSON data
    json_path = Path(__file__).parent.parent / "data" / "results" / "laptops.json"
    with open(json_path, "r", encoding="utf-8") as f:
        laptops_data = json.load(f)

    # 3. Get prompts from database (ordered by ID for consistent mapping)
    result = await session.execute(
        select(Prompt)
        .where(Prompt.topic_id == 2)
        .order_by(Prompt.id.asc())
    )
    prompts = result.scalars().all()

    # 4. Build evaluations
    evaluations = []
    for idx, laptop_data in enumerate(laptops_data):
        if idx >= len(prompts):
            break  # Safety check

        prompt = prompts[idx]
        answers = laptop_data.get("answers", [])
        if not answers:
            continue  # Skip if no answers

        # Use first answer
        answer = answers[0]

        # Skip if timestamp is missing
        if "timestamp" not in answer:
            continue

        # Parse timestamp and calculate dates
        completed_at = datetime.fromisoformat(answer["timestamp"])
        claimed_at = completed_at - timedelta(hours=1)
        created_at = completed_at - timedelta(hours=2)

        # Build answer JSON
        answer_json = {
            "response": answer["response"],
            "citations": answer["citations"],
            "timestamp": answer["timestamp"]
        }

        # Create evaluation
        evaluation = PromptEvaluation(
            prompt_id=prompt.id,
            assistant_plan_id=1,  # ChatGPT Free
            status=EvaluationStatus.COMPLETED,
            answer=answer_json,
            created_at=created_at,
            claimed_at=claimed_at,
            completed_at=completed_at,
        )
        evaluations.append(evaluation)

    # 5. Bulk insert
    if evaluations:
        session.add_all(evaluations)
        await session.flush()

        # 6. Reset sequence
        await session.execute(
            text(
                "SELECT setval('prompt_evaluations_id_seq', "
                "(SELECT MAX(id) FROM prompt_evaluations))"
            )
        )


async def seed_superuser(session: AsyncSession) -> None:
    """
    Seed the first superuser if it doesn't exist.

    Args:
        session: AsyncSession to use for database operations
    """
    from src.auth.crud import create_user, get_user_by_email
    from src.auth.models import UserCreate
    from src.config.settings import settings

    user = await get_user_by_email(session, settings.first_superuser_email)
    if not user:
        user_in = UserCreate(
            email=settings.first_superuser_email,
            password=settings.first_superuser_password,
            is_superuser=True,
        )
        await create_user(session, user_in)
