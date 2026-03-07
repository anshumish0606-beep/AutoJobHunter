from bytez import Bytez
import json
import re


class GeminiClient:
    """
    AI Brain of AutoJobHunter.
    Uses Bytez API for job relevance checking.
    Uses smart fallback selectors for browser navigation (no vision needed).
    """

    def __init__(self, api_key: str):
        client = Bytez(api_key)
        self.model = client.model("Qwen/Qwen2-7B-Instruct")
        print("✅ Bytez AI Brain initialized!")

    def _ask(self, prompt: str) -> str:
        """Send a text prompt to Bytez and return response."""
        try:
            result = self.model.run(prompt)
            if result.error:
                return ""
            return result.output or ""
        except Exception as e:
            print(f"⚠️ Bytez API error: {e}")
            return ""

    def analyze_screenshot(self, screenshot_bytes: bytes, instruction: str) -> dict:
        return {"found": False}

    def find_login_fields(self, screenshot_bytes: bytes) -> dict:
        return {"found": False}

    def find_password_field(self, screenshot_bytes: bytes) -> dict:
        return {"found": False}

    def find_login_button(self, screenshot_bytes: bytes) -> dict:
        return {"found": False}

    def find_search_bar(self, screenshot_bytes: bytes) -> dict:
        return {"found": False}

    def find_filter_option(self, screenshot_bytes: bytes, filter_name: str) -> dict:
        return {"found": False}

    def check_captcha(self, screenshot_bytes: bytes) -> bool:
        return False

    def extract_job_listings(self, screenshot_bytes: bytes) -> dict:
        return {"found": True}

    def is_login_successful(self, screenshot_bytes: bytes) -> bool:
        return True

    def is_job_relevant(self, job_title: str, job_description: str, target_roles: list) -> dict:
        """Use Bytez AI to check if a job is relevant for a fresher candidate."""
        prompt = f"""You are a job relevance checker for a FRESHER candidate in India.

TARGET ROLES: {', '.join(target_roles)}
CANDIDATE: Fresher, 0 years experience, looking for internship or entry-level jobs

JOB TITLE: {job_title}
JOB INFO: {job_description[:300]}

Answer ONLY in this exact JSON format with no extra text:
{{"relevant": true, "relevance_score": "high", "reason": "matches data analyst role", "requires_experience": false}}

Rules:
- relevant: true if job matches any target role and suits a fresher
- relevance_score: high/medium/low
- requires_experience: true if job needs 1+ years experience
- If requires_experience is true, set relevant to false"""

        response = self._ask(prompt)

        try:
            match = re.search(r'\{.*?\}', response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass

        return {
            "relevant": True,
            "relevance_score": "medium",
            "reason": "Could not analyze",
            "requires_experience": False
        }
