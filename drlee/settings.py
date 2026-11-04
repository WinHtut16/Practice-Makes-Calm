"""Django settings for the Dr. Lee rehearsal study app."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env if python-dotenv is installed (optional).
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass


def env(name, default=None):
    return os.environ.get(name, default)


SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = env("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [h for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "study",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "drlee.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "drlee.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / env("DB_NAME", "db.sqlite3"),
    }
}

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Bangkok"
USE_I18N = False
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/admin/login/"

# ---------------------------------------------------------------------------
# Study settings. Freeze these after pilot stage P4 (paper, Section 3.7).
# ---------------------------------------------------------------------------
STUDY = {
    # LLM provider: "anthropic" (Claude, paid; default) or "gemini"
    "PROVIDER": env("LLM_PROVIDER", "anthropic"),
    "ANTHROPIC_API_KEY": env("ANTHROPIC_API_KEY", ""),
    "GEMINI_API_KEY": env("GEMINI_API_KEY", ""),
    # One pinned model for every role (Dr. Lee, judge, scorer). Freeze after pilot P4.
    "MODEL": env("LLM_MODEL", "claude-sonnet-5-5" if env("LLM_PROVIDER", "anthropic") == "anthropic" else "gemini-2.5-flash"),
    # Claude only: effort level (low / medium / high). "low" keeps Dr. Lee's replies fast. Empty = model default.
    "CLAUDE_EFFORT": env("LLM_EFFORT", "low"),
    # Gemini only: integer = thinking budget (e.g. 0), word = thinking level (e.g. "low").
    "THINKING": env("GEMINI_THINKING", ""),
    # Mock mode runs everything without any API calls (for UI testing and the test suite).
    "MOCK": env("LLM_MOCK", "") == "1",
    # Temperatures apply to Gemini only; the current Claude API has no temperature setting.
    "TEMP_DR_LEE": float(env("TEMP_DR_LEE", "0.7")),
    "TEMP_JUDGE": 0.0,
    "MAX_RETRIES": 2,
    # Practice rounds per block, and when a round ends (agreement, 5 learner messages, or 4 minutes)
    "PRACTICE_ROUNDS": int(env("PRACTICE_ROUNDS", "3")),  # 3 since pilot P4: two adaptive decisions per block
    # Optional one-line note between practice rounds ("What will you try next round?"). Same for every design.
    "REFLECTION_PROMPT": env("REFLECTION_PROMPT", "0") == "1",  # off since pilot P4: nobody used it
    "ROUND_SECONDS": int(env("ROUND_SECONDS", "240")),
    "ROUND_MAX_MESSAGES": int(env("ROUND_MAX_MESSAGES", "5")),
    "BREAK_SECONDS": int(env("BREAK_SECONDS", "60")),
    # Adaptive controller (provisional thresholds)
    "ADAPTIVE_START_LEVEL": int(env("ADAPTIVE_START_LEVEL", "2")),
    "LOWER_IF_STRESS_GE": 8,
    "LOWER_IF_DESC_LE": 2,
    "RAISE_IF_STRESS_LE": 6,
    "RAISE_IF_DESC_GE": 5,  # was 6; in pilot P4 the best judge score was 5, so "raise" could never fire
    # Stress tap at or above this offers a pause and alerts the researcher
    "PAUSE_IF_STRESS_GE": 9,
    # Main study: the 5 counterbalancing sequences used (P01, P06, P08 form a balanced 3x3 square; P10, P15 add two).
    "MAIN_SEQUENCES": [int(x) for x in env("MAIN_SEQUENCES", "1,6,8,10,15").split(",")],
    # Which laptop this is. Each laptop owns some of the main sequences, so two laptops never hand out the same
    # participant ID. Example: laptop A  STATION=A, STATION_SEQUENCES=1,8,15 ; laptop B  STATION=B, STATION_SEQUENCES=6,10.
    # Empty STATION_SEQUENCES = this laptop may use all main sequences (only safe if a single laptop runs the study).
    "STATION": env("STATION", "A").strip().upper()[:4] or "A",
    "STATION_SEQUENCES": [int(x) for x in env("STATION_SEQUENCES", "").split(",") if x.strip()],
    # Seed for the random order of arrival within each group of sequences
    "ASSIGNMENT_SEED": int(env("ASSIGNMENT_SEED", "2026")),
}

# Fall back to mock mode when the selected provider has no key, so the app never crashes on startup.
_key = STUDY["ANTHROPIC_API_KEY"] if STUDY["PROVIDER"] == "anthropic" else STUDY["GEMINI_API_KEY"]
if not _key:
    STUDY["MOCK"] = True
STUDY["PROVIDER_LABEL"] = "Anthropic Claude" if STUDY["PROVIDER"] == "anthropic" else "Google Gemini"
