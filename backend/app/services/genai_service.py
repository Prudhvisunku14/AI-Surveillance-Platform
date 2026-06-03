"""GenAI layer — exact spec prompt and output format section 10."""
import json
from typing import Optional
from app.core.config import get_settings

settings = get_settings()

# ── Exact spec prompt ─────────────────────────────────────────
INCIDENT_SUMMARY_PROMPT = """You are an expert security intelligence analyst.
Given the following structured surveillance event, produce a concise, professional incident report.

Event Data:
{event_json}

Respond in JSON with exactly these fields:
- "incident_summary": 2-3 sentence plain-English description of the incident
- "classification_reasoning": chain-of-thought explanation for the severity level
- "recommended_action": specific, actionable guidance for the security operator
- "confidence_note": any caveats about AI confidence or data quality"""


async def generate_incident_summary(event: dict) -> Optional[dict]:
    """
    Calls OpenAI GPT-4o with exact spec prompt.
    Falls back to rule-based if OPENAI unavailable — spec: graceful degradation.
    """
    if settings.genai_enabled and settings.openai_api_key:
        result = await _call_openai(event)
        if result:
            return result

    return _rule_based_summary(event)


async def _call_openai(event: dict) -> Optional[dict]:
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        event_json = json.dumps(event, indent=2, default=str)
        prompt = INCIDENT_SUMMARY_PROMPT.format(event_json=event_json)

        response = await client.chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=600,
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception:
        return None


def _rule_based_summary(event: dict) -> dict:
    """
    Fallback — spec: graceful degradation when LLM unavailable.
    Produces same 4-field output structure as spec.
    """
    etype = event.get("event_type", "unknown")
    severity = event.get("severity", "L1")
    threat = event.get("threat_score", 0.0)
    persons = event.get("persons_involved", [])
    zone_id = event.get("zone_id", "unknown zone")

    person_str = "An unknown individual"
    if persons:
        p = persons[0]
        name = p.get("display_name", "Unknown")
        cat = p.get("category", "")
        conf = p.get("face_confidence", 0.0)
        dur = p.get("duration_in_zone_seconds", 0)
        person_str = (f"{name}" + (f" ({cat})" if cat else "") +
                      (f" [confidence: {conf:.2f}]" if conf > 0 else "") +
                      (f" — present for {dur:.0f}s" if dur > 0 else ""))

    summaries = {
        "loitering_warning": (
            f"{person_str} has been stationary in zone {zone_id} for an extended period, "
            f"exceeding the 120-second loitering threshold. This behaviour is anomalous for the location.",
            f"Classified as {severity} due to prolonged stationary presence beyond policy threshold. "
            f"Threat score: {threat:.2f}.",
            f"Review camera feed for zone {zone_id}. Approach individual if presence continues.",
        ),
        "loitering_critical": (
            f"{person_str} has remained in zone {zone_id} for over 300 seconds, triggering a critical loitering alert. "
            f"Immediate intervention is required.",
            f"Classified as {severity}: extended unauthorised presence beyond critical threshold. Threat score: {threat:.2f}.",
            f"Dispatch security officer to zone {zone_id} immediately. Review all access logs for this zone.",
        ),
        "zone_violation": (
            f"{person_str} was detected in restricted zone {zone_id} without authorisation. "
            f"No corresponding access event was recorded.",
            f"Classified as {severity}: individual's access category does not permit entry. Threat score: {threat:.2f}.",
            f"Dispatch officer to zone {zone_id}. Review door access logs from ±5 minutes.",
        ),
        "suspect_detected": (
            f"A high-risk individual ({person_str}) has been identified in zone {zone_id} via face recognition. "
            f"This person is flagged in the watchlist.",
            f"Classified as {severity} (mandatory L3 override): watchlist match detected. Threat score: {threat:.2f}.",
            f"IMMEDIATE RESPONSE REQUIRED. Alert supervisor. Do not approach alone. Secure zone {zone_id}.",
        ),
        "identity_unknown": (
            f"An unidentified individual in zone {zone_id} could not be matched to any known person after 3 recognition attempts. "
            f"Identity remains unknown.",
            f"Classified as {severity}: face recognition confidence below 0.60 threshold after maximum attempts. "
            f"Threat score: {threat:.2f}.",
            f"Approach individual for identity verification. Request official ID.",
        ),
        "tailgating_detected": (
            f"Multiple individuals entered zone {zone_id} simultaneously on a single access credential. "
            f"Tailgating behaviour detected.",
            f"Classified as {severity} (mandatory L3 override): multi-person entry on single access event. "
            f"Threat score: {threat:.2f}.",
            f"Lock zone {zone_id} immediately. Review entry footage. Investigate credential misuse.",
        ),
        "identity_mismatch": (
            f"The identity recorded by the access sensor does not match the face detected in video for zone {zone_id}. "
            f"Credential misuse suspected.",
            f"Classified as {severity}: sensor person ID differs from video face recognition result. "
            f"Threat score: {threat:.2f}.",
            f"Suspend access credential immediately. Escalate to security manager.",
        ),
        "abandoned_object": (
            f"A stationary object has been detected in zone {zone_id} for over 60 seconds after the person "
            f"who placed it has left the frame.",
            f"Classified as {severity} (mandatory L3 override): unattended object policy violation. "
            f"Threat score: {threat:.2f}.",
            f"Evacuate zone {zone_id} as precaution. Security sweep required before re-entry.",
        ),
        "crowd_alert": (
            f"Zone {zone_id} has exceeded its maximum permitted occupancy. Crowd formation detected.",
            f"Classified as {severity}: occupancy exceeds zone capacity limit. Threat score: {threat:.2f}.",
            f"Redirect persons away from zone {zone_id}. Monitor for escalation.",
        ),
        "sudden_movement": (
            f"{person_str} exhibited sudden erratic movement in zone {zone_id}, exceeding the velocity anomaly baseline.",
            f"Classified as {severity}: velocity anomaly score above 3-sigma threshold. Threat score: {threat:.2f}.",
            f"Monitor individual closely. Assess whether medical assistance is needed.",
        ),
        "sensor_mismatch": (
            f"A sensor event was recorded at {zone_id} with no corresponding video detection within ±5 seconds.",
            f"Classified as {severity}: sensor trigger without video corroboration — possible system fault or covert entry. "
            f"Threat score: {threat:.2f}.",
            f"Verify sensor health for {zone_id}. Review video feed manually.",
        ),
        "repeated_reappearance": (
            f"{person_str} has been detected more than 3 times in zone {zone_id} within the past hour, "
            f"outside of expected access patterns.",
            f"Classified as {severity}: frequency exceeds access schedule threshold. Threat score: {threat:.2f}.",
            f"Cross-reference with access schedule. Interview individual if pattern continues.",
        ),
    }

    default = (
        f"Surveillance event '{etype}' detected in zone {zone_id} involving {person_str}.",
        f"Classified as {severity}. Threat score: {threat:.2f}.",
        f"Review event details and take appropriate action per security policy.",
    )

    summary, reasoning, action = summaries.get(etype, default)

    conf = 0.0
    if persons:
        conf = persons[0].get("face_confidence", 0.0)
    confidence_note = (
        f"Face match confidence: {conf:.2f} — {'reliable' if conf >= 0.82 else 'tentative' if conf >= 0.60 else 'low/unverified'}. "
        "Rule-based fallback active (GenAI API unavailable)."
    )

    return {
        "incident_summary": summary,
        "classification_reasoning": reasoning,
        "recommended_action": action,
        "confidence_note": confidence_note,
    }
