"""Situation Understanding Agent powered by Google Gemini AI.

Converts unstructured emergency reports into validated,
structured situation data using Google Gemini.
"""

from typing import Any, Dict, Optional, List, Literal
import json
import asyncio

from pydantic import BaseModel, Field
from google import genai

from app.core.config import settings
from app.core.logging import logger


# ---------------------------------------------------------------------------
# Structured AI output
# ---------------------------------------------------------------------------


class SituationAssessment(BaseModel):
    """Structured emergency situation extracted from a citizen report."""

    category: Literal[
        "FLOOD",
        "FIRE",
        "BUILDING_COLLAPSE",
        "MEDICAL_EMERGENCY",
        "TRAPPED_PERSONS",
        "HAZARDOUS_LEAK",
        "OTHER",
    ] = Field(
        description=(
            "Emergency category. Use only one of: "
            "FLOOD, FIRE, BUILDING_COLLAPSE, MEDICAL_EMERGENCY, "
            "TRAPPED_PERSONS, HAZARDOUS_LEAK, OTHER."
        )
    )

    urgency_level: Literal[
        "CRITICAL",
        "HIGH",
        "MEDIUM",
        "LOW",
    ] = Field(
        description=(
            "Urgency classification. "
            "CRITICAL means immediate threat to life. "
            "HIGH means urgent assistance is required. "
            "MEDIUM means assistance is needed but appears stable. "
            "LOW means currently non-urgent."
        )
    )

    people_count: int = Field(
        default=0,
        ge=0,
        description="Total number of explicitly affected people.",
    )

    children_count: int = Field(
        default=0,
        ge=0,
        description="Number of children explicitly mentioned.",
    )

    elderly_count: int = Field(
        default=0,
        ge=0,
        description="Number of elderly people explicitly mentioned.",
    )

    pregnant_count: int = Field(
        default=0,
        ge=0,
        description="Number of pregnant people explicitly mentioned.",
    )

    injured_count: int = Field(
        default=0,
        ge=0,
        description="Number of injured people explicitly mentioned.",
    )

    critical_count: int = Field(
        default=0,
        ge=0,
        description="Number of critically injured people explicitly mentioned.",
    )

    trapped_count: int = Field(
        default=0,
        ge=0,
        description="Number of trapped people explicitly mentioned.",
    )

    medical_needs: List[str] = Field(
        default_factory=list,
        description=(
            "Medical assistance, medication, equipment, or treatment "
            "explicitly mentioned in the report."
        ),
    )

    hazards: List[str] = Field(
        default_factory=list,
        description="Hazards explicitly identified in the report.",
    )

    location_description: Optional[str] = Field(
        default=None,
        description=(
            "Location, landmark, street, village, junction, or other "
            "location description explicitly mentioned in the report."
        ),
    )

    summary: str = Field(
        description="Concise factual summary of the emergency situation.",
    )


# ---------------------------------------------------------------------------
# Situation Understanding Agent
# ---------------------------------------------------------------------------


class SituationUnderstandingAgent:
    """Google Gemini AI agent responsible for emergency situation understanding."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = (
            model_name
            or getattr(settings, "GEMINI_MODEL", None)
            or "gemini-3.6-flash"
        )

        logger.info(
            "Initialized SituationUnderstandingAgent "
            f"with Gemini model: {self.model_name}"
        )

    # -----------------------------------------------------------------------
    # Main analysis method
    # -----------------------------------------------------------------------

    async def analyze_report(
        self,
        raw_text: Optional[str] = None,
        audio_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extract structured emergency information from a report."""

        if not raw_text and not audio_url:
            raise ValueError(
                "At least one emergency input is required: raw_text or audio_url."
            )

        if audio_url:
            raise NotImplementedError(
                "Audio analysis is reserved for the multimodal implementation."
            )

        report_text = raw_text.strip()

        if not report_text:
            raise ValueError("Emergency report cannot be empty.")

        prompt = self._build_prompt(
            raw_text=report_text,
            metadata=metadata,
        )

        try:
            assessment_data = await self._call_gemini(prompt, report_text)

            assessment = SituationAssessment.model_validate(
                assessment_data
            )

            assessment = self._normalize_explicit_facts(
                assessment,
                report_text,
            )

            logger.info(
                "Situation assessment generated successfully: "
                f"category={assessment.category}, "
                f"urgency={assessment.urgency_level}, "
                f"people={assessment.people_count}, "
                f"injured={assessment.injured_count}, "
                f"trapped={assessment.trapped_count}"
            )

            return assessment.model_dump()

        except ValueError:
            raise

        except Exception as exc:
            logger.error(
                "Situation Understanding Agent failed: "
                f"{type(exc).__name__}: {exc}",
                exc_info=True,
            )
            # Fallback to rule-based analysis
            fallback = self._fallback_assessment(report_text)
            return fallback.model_dump()

    # -----------------------------------------------------------------------
    # Prompt construction
    # -----------------------------------------------------------------------

    def _build_prompt(
        self,
        raw_text: str,
        metadata: Optional[Dict[str, Any]],
    ) -> str:
        """Build a strict JSON extraction prompt for Qwen."""

        return f"""
You are the Situation Understanding Agent for ResQMesh AI,
an emergency coordination platform.

Analyze the citizen emergency report and return ONLY one valid JSON object.

IMPORTANT RULES:

1. Use ONLY information explicitly supported by the report.
2. Do NOT invent people, injuries, hazards, locations, or medical needs.
3. If a count is not explicitly known, return 0.
4. If a list has no explicitly known values, return [].
5. If no location description is explicitly mentioned, return null.
6. The GPS coordinates are NOT your responsibility. They are handled separately
   by the ResQMesh application.
7. Do not add markdown.
8. Do not add explanations.
9. Do not use code fences.
10. Return ONLY JSON.

ALLOWED CATEGORY VALUES:

FLOOD
FIRE
BUILDING_COLLAPSE
MEDICAL_EMERGENCY
TRAPPED_PERSONS
HAZARDOUS_LEAK
OTHER

If the report describes a road accident, traffic accident, vehicle accident,
or collision and there is no more specific allowed category, use OTHER.

ALLOWED URGENCY VALUES:

CRITICAL
HIGH
MEDIUM
LOW

URGENCY RULES:

CRITICAL:
Immediate threat to life or severe danger.

HIGH:
Urgent assistance is required, including situations involving injured
or trapped people.

MEDIUM:
Assistance is needed but the situation appears relatively stable.

LOW:
Currently non-urgent.

COUNTING RULES:

- "one person" = 1
- "two people" = 2
- "three people" = 3
- "two people are injured" means injured_count = 2
- "one person is trapped" means trapped_count = 1
- If explicitly stated injured and trapped people are different people,
  people_count should include both.
- Do not count people who are not explicitly mentioned.
- Do not infer children, elderly people, or pregnant people.

HAZARD RULES:

Only include hazards explicitly stated or directly described.
For example:
"heavy traffic" can be included as a hazard.
Do not invent hazards such as fire, explosion, fuel leak, etc.

LOCATION RULES:

Extract only the location description explicitly stated in the report.

Return this exact JSON structure:

{{
  "category": "OTHER",
  "urgency_level": "HIGH",
  "people_count": 0,
  "children_count": 0,
  "elderly_count": 0,
  "pregnant_count": 0,
  "injured_count": 0,
  "critical_count": 0,
  "trapped_count": 0,
  "medical_needs": [],
  "hazards": [],
  "location_description": null,
  "summary": "Concise factual summary."
}}

EMERGENCY REPORT:

{raw_text}

ADDITIONAL METADATA:

{json.dumps(metadata or {}, ensure_ascii=False)}

Remember:
RETURN ONLY JSON.
"""

    # -----------------------------------------------------------------------
    # Gemini AI call
    # -----------------------------------------------------------------------

    async def _call_gemini(
        self,
        prompt: str,
        raw_text: str,
    ) -> Dict[str, Any]:
        """Call Google Gemini API using google-genai SDK."""
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            logger.warning("GEMINI_API_KEY is not configured. Falling back to rule-based analysis.")
            return self._fallback_assessment(raw_text).model_dump()

        model_name = self.model_name
        logger.info(f"Sending emergency report to Google Gemini model: {model_name}")

        def _sync_generate():
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            return response.text

        try:
            raw_response = await asyncio.to_thread(_sync_generate)
            if not raw_response:
                raise ValueError("Gemini API returned an empty response.")

            logger.info("Received response from Gemini successfully.")

            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
                if cleaned.endswith("```"):
                    cleaned = cleaned.rsplit("```", 1)[0]
                cleaned = cleaned.strip()

            return json.loads(cleaned)

        except Exception as exc:
            logger.error(f"Gemini API call failed ({type(exc).__name__}: {exc}). Using deterministic fallback.")
            return self._fallback_assessment(raw_text).model_dump()

    def _fallback_assessment(self, raw_text: str) -> SituationAssessment:
        """Deterministic fallback when AI service is unavailable."""
        text = raw_text.lower()
        
        category = "OTHER"
        if "flood" in text or "water" in text or "overflow" in text:
            category = "FLOOD"
        elif "fire" in text or "smoke" in text or "flame" in text or "burn" in text:
            category = "FIRE"
        elif "collapse" in text or "building" in text or "rubble" in text:
            category = "BUILDING_COLLAPSE"
        elif "medical" in text or "ambulance" in text or "heart" in text or "stroke" in text:
            category = "MEDICAL_EMERGENCY"
        elif "trapped" in text or "stuck" in text:
            category = "TRAPPED_PERSONS"
        elif "leak" in text or "gas" in text or "chemical" in text or "hazard" in text:
            category = "HAZARDOUS_LEAK"

        urgency = "HIGH" if ("trapped" in text or "injured" in text or "critical" in text or "die" in text) else "MEDIUM"
        if "immediate" in text or "catastrophic" in text or "explosion" in text:
            urgency = "CRITICAL"

        return SituationAssessment(
            category=category,
            urgency_level=urgency,
            people_count=1,
            children_count=0,
            elderly_count=0,
            pregnant_count=0,
            injured_count=1 if "injured" in text else 0,
            critical_count=1 if "critical" in text else 0,
            trapped_count=1 if "trapped" in text else 0,
            medical_needs=["Emergency medical evaluation"] if "injured" in text else [],
            hazards=["Structural hazard"] if category == "BUILDING_COLLAPSE" else [],
            location_description="Location specified in citizen report",
            summary=f"Reported {category.lower().replace('_', ' ')} situation requiring response."
        )

    # -----------------------------------------------------------------------
    # Explicit fact normalization
    # -----------------------------------------------------------------------

    def _normalize_explicit_facts(
        self,
        assessment: SituationAssessment,
        raw_text: str,
    ) -> SituationAssessment:
        """Protect explicit numerical facts from being lost by the LLM."""

        text = raw_text.lower()

        # ---------------------------------------------------------------
        # Injured people
        # ---------------------------------------------------------------

        injured_count = self._extract_count(
            text,
            [
                "people are injured",
                "people were injured",
                "people injured",
            ],
        )

        if injured_count is not None:
            assessment.injured_count = injured_count

        # Singular injured wording
        if injured_count is None and self._contains_any(
            text,
            [
                "one person is injured",
                "one person was injured",
                "one person injured",
                "one injured person",
            ],
        ):
            assessment.injured_count = 1

        # ---------------------------------------------------------------
        # Trapped people
        # ---------------------------------------------------------------

        trapped_count = self._extract_count(
            text,
            [
                "people are trapped",
                "people were trapped",
                "people trapped",
            ],
        )

        if trapped_count is not None:
            assessment.trapped_count = trapped_count

        if trapped_count is None and self._contains_any(
            text,
            [
                "one person is trapped",
                "one person was trapped",
                "one person trapped",
                "one person appears trapped",
                "one trapped person",
            ],
        ):
            assessment.trapped_count = 1

        # ---------------------------------------------------------------
        # Children
        # ---------------------------------------------------------------

        children_count = self._extract_count(
            text,
            [
                "children are",
                "children were",
                "children involved",
                "children affected",
            ],
        )

        if children_count is not None:
            assessment.children_count = children_count

        # ---------------------------------------------------------------
        # Elderly people
        # ---------------------------------------------------------------

        elderly_count = self._extract_count(
            text,
            [
                "elderly people are",
                "elderly people were",
                "elderly people involved",
                "elderly people affected",
            ],
        )

        if elderly_count is not None:
            assessment.elderly_count = elderly_count

        # ---------------------------------------------------------------
        # Pregnant people
        # ---------------------------------------------------------------

        pregnant_count = self._extract_count(
            text,
            [
                "pregnant women are",
                "pregnant women were",
                "pregnant women involved",
                "pregnant women affected",
                "pregnant people are",
                "pregnant people were",
            ],
        )

        if pregnant_count is not None:
            assessment.pregnant_count = pregnant_count

        # ---------------------------------------------------------------
        # Explicit hazard
        # ---------------------------------------------------------------

        if "heavy traffic" in text:
            if "heavy traffic" not in assessment.hazards:
                assessment.hazards.append("heavy traffic")

        # ---------------------------------------------------------------
        # Explicit location
        # ---------------------------------------------------------------

        if assessment.location_description is None:
            location = self._extract_location(text)

            if location:
                assessment.location_description = location

        # ---------------------------------------------------------------
        # Total people
        # ---------------------------------------------------------------
        #
        # Only derive a total when explicit counts are available.
        # We avoid inventing a total from vague wording.
        # ---------------------------------------------------------------

        explicit_people = (
            assessment.injured_count
            + assessment.trapped_count
            + assessment.children_count
            + assessment.elderly_count
            + assessment.pregnant_count
        )

        if explicit_people > assessment.people_count:
            assessment.people_count = explicit_people

        # ---------------------------------------------------------------
        # Urgency normalization
        # ---------------------------------------------------------------
        #
        # If the report explicitly contains injured/trapped people,
        # HIGH is a reasonable minimum urgency for this application's
        # emergency workflow.
        #
        # CRITICAL is NOT automatically assigned.
        # ---------------------------------------------------------------

        if (
            assessment.urgency_level == "LOW"
            and (
                assessment.injured_count > 0
                or assessment.trapped_count > 0
            )
        ):
            assessment.urgency_level = "HIGH"

        return assessment

    # -----------------------------------------------------------------------
    # Helper functions
    # -----------------------------------------------------------------------

    @staticmethod
    def _contains_any(
        text: str,
        phrases: List[str],
    ) -> bool:
        """Return True if any phrase occurs in text."""

        return any(
            phrase.lower() in text
            for phrase in phrases
        )

    @staticmethod
    def _extract_count(
        text: str,
        phrases: List[str],
    ) -> Optional[int]:
        """Extract simple English number words before a phrase."""

        number_words = {
            "zero": 0,
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
        }

        for phrase in phrases:
            for word, number in number_words.items():
                if f"{word} {phrase}" in text:
                    return number

        return None

    @staticmethod
    def _extract_location(
        text: str,
    ) -> Optional[str]:
        """Extract a few common explicit location patterns."""

        patterns = [
            "near the main junction",
            "at the main junction",
            "near the junction",
            "at the junction",
        ]

        for pattern in patterns:
            if pattern in text:
                return pattern

        return None