from .start import router as start_router
from .checklist import router as checklist_router
from .goals import router as goals_router
from .progress import router as progress_router
from .mood import router as mood_router
from .schedule import router as schedule_router

def register_handlers(dp):
    dp.include_router(start_router)
    dp.include_router(checklist_router)
    dp.include_router(goals_router)
    dp.include_router(progress_router)
    dp.include_router(mood_router)
    dp.include_router(schedule_router)
