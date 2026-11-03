import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from app.core.config import settings
from app.core.init_db import init_db
from app.core.database import async_session_factory
from app.api.router import api_router
from app.services.redmine_service import redmine_service
from app.services.notification_service import notification_service
from app.models.alert_config import AlertRecipientConfig


async def ensure_alert_config():
    """
    Idempotent: Ensures the AlertRecipientConfig table has at least one active
    recipient row. Runs every startup — safe even if DB was already seeded.
    """
    async with async_session_factory() as db:
        existing = (
            await db.execute(
                select(AlertRecipientConfig)
                .where(AlertRecipientConfig.is_active == True)
                .limit(1)
            )
        ).scalars().first()

        if not existing:
            config = AlertRecipientConfig(
                label="Default Admin Recipient",
                recipient_email=settings.DEFAULT_ALERT_EMAIL,
                recipient_name=settings.DEFAULT_ALERT_NAME,
                google_chat_webhook_url=settings.GOOGLE_CHAT_ADMIN_WEBHOOK_URL or None,
                in_app_enabled=True,
                google_chat_enabled=True,
                email_enabled=True,
                is_active=True,
            )
            db.add(config)
            await db.commit()
            print(f"[Startup] Alert recipient config seeded -> {settings.DEFAULT_ALERT_EMAIL}")
        else:
            print(f"[Startup] Alert recipient config OK -> {existing.recipient_email}")


async def background_periodic_sync():
    """
    Continuous background loop:
    Runs every 5 minutes to synchronize Redmine and automatically generate
    operational alerts for the Administrator.
    """
    while True:
        try:
            await asyncio.sleep(settings.REDMINE_SYNC_INTERVAL_MINUTES * 60)
            async with async_session_factory() as db:
                await redmine_service.sync_all(db)
            # Generate automated alerts after every sync
            async with async_session_factory() as db:
                alerts = await notification_service.generate_automated_alerts(db)
                if alerts:
                    print(f"[PeriodicSync] {len(alerts)} new alert(s) generated.")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[PeriodicSync] Background sync notice: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup: Initialize DB and seeds if required
    await init_db()

    # 2. Ensure AlertRecipientConfig exists (safe on already-seeded DB)
    await ensure_alert_config()

    # 3. Perform initial live Redmine sync & automated alert generation
    try:
        async with async_session_factory() as db:
            print("[Startup] Triggering initial Redmine sync & automated alert generation...")
            sync_res = await redmine_service.sync_all(db)
            print(f"[Startup] Redmine sync complete: {sync_res}")

        # Run initial alert scan after sync
        async with async_session_factory() as db:
            alerts = await notification_service.generate_automated_alerts(db)
            print(f"[Startup] {len(alerts)} automated alert(s) generated on startup.")
    except Exception as e:
        print(f"[Startup] Initial sync/alert warning: {e}")

    # 4. Start background periodic monitor
    sync_task = asyncio.create_task(background_periodic_sync())

    yield

    # Shutdown logic
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise Project, Team, Employee & AI-Powered Management System (Admin Dedicated Mode)",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "mode": "admin-centric"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
