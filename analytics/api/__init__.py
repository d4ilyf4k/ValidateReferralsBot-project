from .router import router
from .summary import router as summary_router

router.include_router(summary_router)
