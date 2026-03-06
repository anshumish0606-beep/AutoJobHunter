import google.generativeai as genai
import base64
import json
import re
from pathlib import Path


class GeminiClient:
    """
    AI Brain of AutoJobHunter.
    Uses Gemini Vision to understand any webpage screenshot
    and find login fields, search bars, filters intelligently.
    """

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        print("✅ Gemini AI Brain initialized!")

    def analyze_screenshot(self, screenshot_bytes: bytes, instruction: str) -> dict:
        """
        Send screenshot to Gemini and ask it to find UI elements.
        Returns coordinates and element info.
        """
        image_data = base64.b64encode(screenshot_bytes).decode("utf-8")

        prompt = f"""
        You are a web automation assistant. Analyze this webpage screenshot carefully.
        
        TASK: {instruction}
        
        Respond ONLY in this exact JSON format, nothing else:
        {{
            "found": true/false,
            "element_description": "what you found",
            "action": "click/type/select",
            "selector_hint": "describe the element location (top/middle/bottom, left/center/right)",
            "text_near_element": "any text label near the element",
            "confidence": "high/medium/low"
        }}
        
        If multiple elements found, return the most relevant one.
        If not found, set found to false.
        """

        response = self.model.generate_content([
            {"mime_type": "image/png", "data": image_data},
            prompt
        ])

        try:
            text = response.text.strip()
            text = re.sub(r"```json|```", "", text).strip()
            return json.loads(text)
        except Exception:
            return {"found": False, "error": "Could not parse Gemini response"}

    def find_login_fields(self, screenshot_bytes: bytes) -> dict:
        """Ask Gemini to find username and password fields."""
        return self.analyze_screenshot(
            screenshot_bytes,
            "Find the USERNAME or EMAIL input field on this login page. "
            "Look for input fields labeled Email, Username, Mobile, User ID etc."
        )

    def find_password_field(self, screenshot_bytes: bytes) -> dict:
        """Ask Gemini to find the password field."""
        return self.analyze_screenshot(
            screenshot_bytes,
            "Find the PASSWORD input field on this login page."
        )

    def find_login_button(self, screenshot_bytes: bytes) -> dict:
        """Ask Gemini to find the login/submit button."""
        return self.analyze_screenshot(
            screenshot_bytes,
            "Find the LOGIN or SIGN IN button on this page. "
            "It may say: Login, Sign In, Log In, Submit, Continue."
        )

    def find_search_bar(self, screenshot_bytes: bytes) -> dict:
        """Ask Gemini to find the job search bar."""
        return self.analyze_screenshot(
            screenshot_bytes,
            "Find the main JOB SEARCH input field on this job portal page. "
            "Look for fields labeled: Search Jobs, Job Title, Keywords, What, Designation."
        )

    def find_filter_option(self, screenshot_bytes: bytes, filter_name: str) -> dict:
        """Ask Gemini to find a specific filter option."""
        return self.analyze_screenshot(
            screenshot_bytes,
            f"Find the '{filter_name}' filter option on this job search results page. "
            f"Look for dropdowns, checkboxes, or buttons related to {filter_name}."
        )

    def is_login_successful(self, screenshot_bytes: bytes) -> bool:
        """Ask Gemini if login was successful."""
        result = self.analyze_screenshot(
            screenshot_bytes,
            "Is this page showing a LOGGED IN dashboard/home page? "
            "Look for: profile icon, user name, logout button, dashboard. "
            "If yes found=true, if still on login page found=false."
        )
        return result.get("found", False)

    def check_captcha(self, screenshot_bytes: bytes) -> bool:
        """Ask Gemini if there's a CAPTCHA on screen."""
        result = self.analyze_screenshot(
            screenshot_bytes,
            "Is there a CAPTCHA, reCAPTCHA, or human verification challenge visible on this page? "
            "If yes found=true, if no found=false."
        )
        return result.get("found", False)

    def extract_job_listings(self, screenshot_bytes: bytes) -> dict:
        """Ask Gemini to identify if job results are visible."""
        return self.analyze_screenshot(
            screenshot_bytes,
            "Are there job listings/results visible on this page? "
            "Look for job cards with title, company, location. "
            "If yes found=true and describe what you see."
        )

    def is_job_relevant(self, job_title: str, job_description: str, target_roles: list) -> dict:
        """Ask Gemini if a job is relevant to our target roles."""
        prompt = f"""
        You are a job relevance checker for a FRESHER candidate.
        
        TARGET ROLES: {', '.join(target_roles)}
        CANDIDATE PROFILE: Fresher, 0 experience, looking for internship/entry-level
        
        JOB TITLE: {job_title}
        JOB DESCRIPTION SNIPPET: {job_description[:500]}
        
        Respond ONLY in this exact JSON format:
        {{
            "relevant": true/false,
            "relevance_score": "high/medium/low",
            "reason": "brief reason why relevant or not",
            "requires_experience": true/false
        }}
        """

        response = self.model.generate_content(prompt)
        try:
            text = response.text.strip()
            text = re.sub(r"```json|```", "", text).strip()
            return json.loads(text)
        except Exception:
            return {"relevant": True, "relevance_score": "medium", "reason": "Could not analyze", "requires_experience": False}
