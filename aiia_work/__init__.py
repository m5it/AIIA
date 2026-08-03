#
# aiia_work — marketplace client (projects / requests / API keys).
# Standalone, opt-in feature. Only loaded when the user starts the
# program with `python run.py --work`.
#
from aiia_work.client import WorkClient, WorkError

__version__ = "0.1.0"

__all__ = ["WorkClient", "WorkError", "__version__"]
