"""
Prompt templates for CivicFlow AI complaint extraction.

All prompts used by the LLM module are defined here.
This separation ensures:
    - Prompt engineers can iterate without touching business logic
    - Prompts are version-controllable independently
    - Easy A/B testing of different prompt strategies
    - Swapping LLMs only requires adjusting prompts, not code

Prompt Design Rationale:
    - SYSTEM_PROMPT: Anchors the model's role, enforces JSON-only output,
      and defines the exact schema. The model is told to NEVER explain —
      this prevents markdown/text leaking into structured responses.
    - USER_PROMPT_TEMPLATE: Fuses complaint text + YOLO detections into
      a single grounded context block. YOLO results are injected as
      structured evidence so the LLM cross-references visual detections
      with textual descriptions for higher accuracy.
    - VISION_ADDENDUM: Extra instruction when an image is attached,
      telling the model to reason over visual content as well.
"""

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT: str = """You are a civic grievance analysis AI for CivicFlow AI, a government complaint management platform.

Your task is to analyze a resident's complaint and extract structured information.

You will receive:
1. The complaint text (may be in English, Hindi, Marathi, or code-mixed)
2. Optionally, YOLO object detection results from an image of the issue
3. Optionally, the image itself for visual analysis

INSTRUCTIONS:
- Extract the following fields from the complaint:
  • category: The type of civic issue (e.g., "Road Damage", "Illegal Parking", "Fallen Tree", "Broken Street Light", "Water Supply", "Garbage", "Drainage", "Traffic Signal", "Public Safety")
  • department: The government department responsible (e.g., "Road Department", "Traffic Department", "Water Supply Department", "Sanitation Department", "Electricity Department", "Parks Department", "Public Works Department")
  • urgency: One of "Critical", "High", "Medium", "Low"
  • location: The location mentioned in the complaint. Extract ANY location reference — landmarks, street names, area names, pin codes.
  • summary: A concise English summary of the complaint in 1-2 sentences, regardless of the input language.
  • confidence: Your confidence score between 0.0 and 1.0 for the overall extraction accuracy.

RULES:
- Return ONLY valid JSON. No markdown. No explanation. No preamble. No trailing text.
- If a field cannot be determined from the input, set its value to null.
- If YOLO detections are provided, cross-reference them with the complaint text for higher accuracy.
- If YOLO detections conflict with the complaint text, prefer the complaint text but lower your confidence score.
- Urgency guidelines:
  • Critical: Immediate safety hazard (e.g., large pothole on highway, fallen tree blocking road, exposed electrical wire)
  • High: Significant inconvenience or potential danger (e.g., broken traffic signal, major road crack)
  • Medium: Notable issue but not immediately dangerous (e.g., damaged road sign, overflowing garbage bin)
  • Low: Minor issue or cosmetic (e.g., faded road marking, small crack in sidewalk)
- Always respond in valid JSON matching this exact schema:
{
    "category": "<string or null>",
    "department": "<string or null>",
    "urgency": "<Critical|High|Medium|Low or null>",
    "location": "<string or null>",
    "summary": "<string or null>",
    "confidence": <float between 0.0 and 1.0>
}"""


# =============================================================================
# USER PROMPT TEMPLATE
# =============================================================================

USER_PROMPT_TEMPLATE: str = """Analyze the following civic complaint and extract structured information.

COMPLAINT TEXT:
{complaint_text}

{yolo_section}

Extract category, department, urgency, location, summary, and confidence.
Return ONLY valid JSON."""


# =============================================================================
# YOLO DETECTION SECTION (injected into user prompt when detections exist)
# =============================================================================

YOLO_DETECTION_SECTION: str = """YOLO IMAGE DETECTION RESULTS:
The following objects were detected in the complaint image by a computer vision model:
{yolo_details}

Use these detection results to cross-reference and validate the complaint text.
If the detections provide additional context not mentioned in the text, incorporate it."""


# =============================================================================
# VISION ADDENDUM (appended when image is provided for vision model analysis)
# =============================================================================

VISION_ADDENDUM: str = """An image of the reported issue is attached.
Analyze the image carefully alongside the complaint text and YOLO detections.
Use visual evidence to improve extraction accuracy and confidence."""


# =============================================================================
# FALLBACK / DEFAULT RESPONSE
# =============================================================================

FALLBACK_RESPONSE: dict = {
    "category": None,
    "department": None,
    "urgency": None,
    "location": None,
    "summary": None,
    "confidence": 0.0,
}


# =============================================================================
# HELPER: Build the YOLO section string from a detection dictionary
# =============================================================================

def format_yolo_detections(yolo_detection: dict | None) -> str:
    """
    Format YOLO detection results into a human-readable string
    for injection into the user prompt.

    Args:
        yolo_detection: Dictionary containing YOLO detection results.
            Expected format:
            {
                "detections": [
                    {
                        "class": "Pothole",
                        "confidence": 0.92,
                        "bbox": [x1, y1, x2, y2]  # optional
                    },
                    ...
                ],
                "count": 2,          # optional
                "image_path": "..."  # optional
            }

    Returns:
        Formatted YOLO section string, or empty string if no detections.
    """
    if not yolo_detection:
        return ""

    detections = yolo_detection.get("detections", [])
    if not detections:
        return ""

    yolo_lines: list[str] = []
    for i, det in enumerate(detections, start=1):
        class_name = det.get("class", "Unknown")
        conf = det.get("confidence", 0.0)
        yolo_lines.append(f"  {i}. {class_name} (confidence: {conf:.2f})")

    yolo_details = "\n".join(yolo_lines)

    return YOLO_DETECTION_SECTION.format(yolo_details=yolo_details)


def build_user_prompt(
    complaint_text: str,
    yolo_detection: dict | None = None,
) -> str:
    """
    Assemble the complete user prompt from complaint text and
    optional YOLO detection results.

    Args:
        complaint_text: The resident's complaint text.
        yolo_detection: Optional YOLO detection dictionary.

    Returns:
        Fully assembled user prompt string.
    """
    yolo_section = format_yolo_detections(yolo_detection)

    return USER_PROMPT_TEMPLATE.format(
        complaint_text=complaint_text,
        yolo_section=yolo_section,
    ).strip()
