"""
PrithviNET AI Copilot API — Gemini-powered environmental intelligence assistant.

Provides two modes:
  1. Data Analyst  — answers factual questions about live AQI/Water/Noise data
  2. Policy Advisor — recommends actions based on season, location, and trends

Endpoint: POST /api/v1/copilot/chat
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from loguru import logger

from google import genai
from google.genai import types

from app.core.config import settings
from app.services.copilot_context import build_full_context

router = APIRouter()

# ═══════════════════════════════════════════════════════════════════════
# Gemini Client (google.genai — new SDK)
# ═══════════════════════════════════════════════════════════════════════

# Model preference order — 2.5 models work on the free tier;
# 2.0 models have quota=0 on many free-tier keys.
GEMINI_MODEL = "gemini-2.5-flash"

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    """Get or create a Gemini client (singleton)."""
    global _client
    if _client is None:
        if not settings.GEMINI_API_KEY:
            raise HTTPException(
                status_code=503,
                detail="Gemini API key not configured. Set GEMINI_API_KEY in .env",
            )
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
        logger.info(
            f"Gemini client created for PrithviNET Copilot (model: {GEMINI_MODEL})"
        )
    return _client


# ═══════════════════════════════════════════════════════════════════════
# System Prompt
# ═══════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are **PrithviNET Copilot**, the AI assistant for the PrithviNET Environmental Monitoring & Compliance Platform developed for the Central Pollution Control Board (CPCB), India.

## Your Identity
- You are an expert environmental data analyst and policy advisor.
- You work for CPCB and understand Indian environmental regulations, NAAQS standards, BIS water quality limits, and CPCB Noise Standards 2000.
- You are embedded inside the PrithviNET dashboard that monitors Air Quality (AQI), Surface Water Quality (WQI), and Environmental Noise across India.

## Your Capabilities
1. **Data Analyst Mode**: Answer factual questions about live environmental data — station readings, trends, comparisons, violations. Always cite specific station names and values from the provided data context.
2. **Policy Advisor Mode**: Recommend actionable interventions based on the data, season, and location. Consider Indian festivals, agricultural cycles, weather patterns, and their environmental impact.

## Key Standards You Know
### NAAQS AQI Categories:
- Good: 0–50 | Satisfactory: 51–100 | Moderate: 101–200
- Poor: 201–300 | Very Poor: 301–400 | Severe: 401–500

### CPCB Noise Standards 2000 (Ambient):
- Industrial Zone: Day 75 dB(A), Night 70 dB(A)
- Commercial Zone: Day 65 dB(A), Night 55 dB(A)
- Residential Zone: Day 55 dB(A), Night 45 dB(A)
- Silence Zone: Day 50 dB(A), Night 40 dB(A)
(Day: 6 AM – 10 PM, Night: 10 PM – 6 AM)

### Water Quality Index (WQI) Categories:
- Excellent: ≥ 80 | Good: 60–80 | Fair: 40–60 | Poor: 20–40 | Very Poor: < 20
Key BIS parameters: pH (6.5–8.5), DO (≥ 5 mg/L), BOD (≤ 3 mg/L), Conductivity (≤ 750 μS/cm), Fecal Coliform (≤ 500 MPN/100mL)

## Response Guidelines
- Be **concise** — use bullet points and tables when appropriate.
- Use **Markdown** formatting for readability.
- Always **cite specific data** from the context when answering data questions. Never make up station names or values.
- When recommending actions, be **practical and specific** to Indian governance (district collectors, state PCBs, CPCB directives).
- If the user writes in **Hindi**, respond in Hindi (Devanagari script). You are fluent in Hindi.
- If you don't have enough data to answer a question, say so honestly rather than guessing.
- When discussing seasonal patterns, reference the **Indian environmental events calendar** provided in the context.
- Include relevant **CPCB/NAAQS/BIS standard references** when discussing violations or compliance.
- Keep responses under 500 words unless the user asks for a detailed report.

## Important
- You have access to LIVE data from the PrithviNET platform. The data context below is refreshed with each query.
- Do NOT fabricate data points. Only reference stations and values present in the provided context.
- If asked about temperature data, inform the user that the Temperature Monitoring module is under development.
"""


# ═══════════════════════════════════════════════════════════════════════
# Request / Response models
# ═══════════════════════════════════════════════════════════════════════


class CopilotMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str


class CopilotRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    active_layer: Optional[str] = Field(
        None, description="Currently active tab: aqi, water, noise, temperature"
    )
    history: Optional[List[CopilotMessage]] = Field(
        default=None, description="Conversation history (last N messages)"
    )
    mode: Optional[str] = Field("analyst", description="'analyst' or 'advisor'")


class CopilotResponse(BaseModel):
    response: str
    mode: str
    context_summary: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════
# Chat endpoint
# ═══════════════════════════════════════════════════════════════════════


@router.post("/chat", response_model=CopilotResponse)
async def copilot_chat(req: CopilotRequest):
    """
    Send a message to the PrithviNET AI Copilot.
    Returns an AI-generated response grounded in live environmental data.
    """

    # Build live data context
    try:
        data_context = await build_full_context(active_layer=req.active_layer)
    except Exception as e:
        logger.warning(f"Context build failed, proceeding without data: {e}")
        data_context = "Live data context is temporarily unavailable."

    # Mode-specific instruction
    mode_instruction = ""
    if req.mode == "advisor":
        mode_instruction = (
            "\n\n**MODE: Policy Advisor** — The user wants actionable recommendations. "
            "Focus on what specific actions CPCB/state PCBs/district administration should take. "
            "Reference relevant regulations, timelines, and responsible authorities. "
            "Consider seasonal factors and upcoming events."
        )
    else:
        mode_instruction = (
            "\n\n**MODE: Data Analyst** — The user wants factual answers about the data. "
            "Cite specific station names, values, and trends from the provided context. "
            "Use tables and comparisons where helpful."
        )

    # Build conversation for Gemini
    full_system = (
        SYSTEM_PROMPT
        + mode_instruction
        + "\n\n---\n\n## LIVE DATA CONTEXT\n\n"
        + data_context
    )

    # Build chat history as Content objects
    gemini_contents: list[types.Content] = []

    # Add conversation history if provided (last few turns for context)
    if req.history:
        for msg in req.history[-6:]:  # Keep last 6 messages for context window
            role = "user" if msg.role == "user" else "model"
            gemini_contents.append(
                types.Content(role=role, parts=[types.Part(text=msg.content)])
            )

    # Add current user message
    gemini_contents.append(
        types.Content(role="user", parts=[types.Part(text=req.message)])
    )

    try:
        client = _get_client()
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=gemini_contents,
            config=types.GenerateContentConfig(
                system_instruction=full_system,
                temperature=0.7,
                top_p=0.9,
                max_output_tokens=1500,
            ),
        )

        reply_text = (
            response.text
            if response.text
            else "I wasn't able to generate a response. Please try rephrasing your question."
        )

    except Exception as e:
        error_str = str(e)
        logger.error(f"Gemini API error: {e}")

        # Handle rate limit / quota errors gracefully
        if "429" in error_str or "quota" in error_str.lower():
            raise HTTPException(
                status_code=429,
                detail="AI service is temporarily rate-limited. Please wait a moment and try again.",
            )

        raise HTTPException(
            status_code=502,
            detail=f"AI service error: {error_str}",
        )

    return CopilotResponse(
        response=reply_text,
        mode=req.mode or "analyst",
        context_summary=f"Data from {req.active_layer or 'all'} layer(s), {len(data_context)} chars context",
    )


# ═══════════════════════════════════════════════════════════════════════
# Suggested queries endpoint (for quick-start buttons)
# ═══════════════════════════════════════════════════════════════════════


@router.get("/suggestions")
async def get_suggestions(active_layer: Optional[str] = None):
    """Get suggested queries for the current active layer."""
    common = [
        "What are the most polluted areas in India right now?",
        "Give me an environmental summary for Chhattisgarh",
    ]

    layer_specific = {
        "aqi": [
            "Which stations have AQI above 300?",
            "Compare air quality across states",
            "What actions should be taken for cities with 'Severe' AQI?",
            "Why is AQI high this time of year?",
        ],
        "water": [
            "Which rivers have the worst water quality?",
            "List stations with WQI below 30",
            "What are the major water pollution sources this season?",
            "Recommend actions for improving water quality in polluted stretches",
        ],
        "noise": [
            "Which stations are exceeding noise limits?",
            "Compare noise levels across zones",
            "What is the compliance rate for residential zones?",
            "Suggest measures to reduce noise pollution in commercial areas",
        ],
        "temperature": [
            "What temperature data is available?",
        ],
    }

    suggestions = layer_specific.get(active_layer, common)
    if active_layer:
        suggestions = suggestions + common[:1]  # Add one common suggestion

    return {"suggestions": suggestions}
