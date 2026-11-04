from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "List the models your API key can use (pick one exact ID for LLM_MODEL in .env)."

    def handle(self, *args, **opts):
        st = settings.STUDY
        if st["PROVIDER"] == "anthropic":
            if not st["ANTHROPIC_API_KEY"]:
                self.stderr.write("ANTHROPIC_API_KEY is not set (see .env.example).")
                return
            import anthropic
            client = anthropic.Anthropic(api_key=st["ANTHROPIC_API_KEY"])
            for m in client.models.list(limit=100):
                self.stdout.write(f"{m.id}\t{getattr(m, 'display_name', '')}")
        else:
            if not st["GEMINI_API_KEY"]:
                self.stderr.write("GEMINI_API_KEY is not set (see .env.example).")
                return
            from google import genai
            client = genai.Client(api_key=st["GEMINI_API_KEY"])
            for m in client.models.list():
                actions = getattr(m, "supported_actions", None) or []
                if not actions or "generateContent" in actions:
                    self.stdout.write(f"{m.name}\t{getattr(m, 'display_name', '')}")
        self.stdout.write(f"\nProvider: {st['PROVIDER']} · currently configured model: {st['MODEL']}")
