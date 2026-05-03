"""Chainlit Claims Intelligence Assistant Interface for Insurance Claims Platform."""

import chainlit as cl
from typing import Optional, Dict, Any
import re
from database_client import DatabaseClient
from embeddings_client import EmbeddingsClient
from watsonx_client import get_watsonx_client
from config import Config
import structlog


structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

config = Config()


class AdjusterAgent:
    """AI Agent for insurance claim adjusters with database-grounded LLM capabilities."""

    def __init__(self):
        self.db_client = DatabaseClient()
        self.embeddings_client = EmbeddingsClient()
        self.conversation_history = []

        try:
            self.watsonx_client = get_watsonx_client()
            self.use_llm = True
            logger.info("watsonx_client_enabled")
        except Exception as e:
            logger.warning("watsonx_client_disabled", error=str(e))
            self.watsonx_client = None
            self.use_llm = False

    async def process_query(self, user_message: str) -> str:
        self.conversation_history.append({"role": "user", "content": user_message})

        try:
            intent = self._detect_intent(user_message)
            claim_number = self._extract_claim_number(user_message)
            entities = {"claim_number": claim_number}

            logger.info("intent_detected", intent=intent, entities=entities)

            database_context = await self._gather_database_context(
                intent=intent,
                entities=entities,
                user_message=user_message
            )

            if database_context and any(database_context.values()):
                response = await self._answer_from_database_context(
                    user_message=user_message,
                    intent=intent,
                    database_context=database_context
                )
            else:
                response = await self._handle_general_query(user_message)

            self.conversation_history.append({"role": "assistant", "content": response})
            return response

        except Exception as e:
            logger.error("query_processing_error", error=str(e))
            error_response = f"❌ Error processing your query: {str(e)}"
            self.conversation_history.append({"role": "assistant", "content": error_response})
            return error_response

    async def _gather_database_context(
        self,
        intent: str,
        entities: Dict[str, Any],
        user_message: str
    ) -> Dict[str, Any]:
        context = {}

        try:
            claim_number = entities.get("claim_number") or self._extract_claim_number(user_message)

            if intent in ["get_claim_details", "find_policyholder"] and claim_number:
                claim = await self.db_client.get_claim_by_number(claim_number)
                if claim:
                    context["claim"] = claim

            elif intent == "find_similar_claims":
                if claim_number:
                    claim = await self.db_client.get_claim_by_number(claim_number)
                    if claim and claim.get("description"):
                        query_text = claim["description"]
                        context["source_claim"] = claim
                    else:
                        query_text = user_message
                else:
                    query_text = user_message

                similar_claims = await self.embeddings_client.find_similar_claims(
                    query_text=query_text,
                    similarity_threshold=0.6,
                    max_results=5
                )

                if similar_claims:
                    context["similar_claims"] = similar_claims

            elif intent == "fraud_detection":
                description = (
                    user_message
                    .replace("fraud", "")
                    .replace("suspicious", "")
                    .replace("fraudulent", "")
                    .strip()
                )

                if claim_number:
                    claim = await self.db_client.get_claim_by_number(claim_number)
                    if claim and claim.get("description"):
                        description = claim["description"]
                        context["source_claim"] = claim

                if len(description) > 10:
                    similar_claims = await self.embeddings_client.find_similar_claims(
                        query_text=description,
                        similarity_threshold=0.65,
                        max_results=10
                    )

                    fraud_patterns = [
                        claim for claim in similar_claims
                        if claim.get("risk_score", 0) > 70
                    ]

                    if fraud_patterns:
                        context["fraud_patterns"] = fraud_patterns

            elif intent == "claim_statistics":
                stats = await self.db_client.get_claim_statistics()
                if stats:
                    context["statistics"] = stats

            elif intent == "high_risk_claims":
                high_risk_claims = await self.db_client.get_high_risk_claims(limit=10)
                if high_risk_claims:
                    context["high_risk_claims"] = high_risk_claims

        except Exception as e:
            logger.error("context_gathering_failed", error=str(e))

        return context

    async def _answer_from_database_context(
        self,
        user_message: str,
        intent: str,
        database_context: Dict[str, Any]
    ) -> str:
        message_lower = user_message.lower()

        if intent == "find_policyholder" and "claim" in database_context:
            claim = database_context["claim"]
            return (
                f"The policyholder for claim **{claim.get('claim_number', 'N/A')}** is "
                f"**{claim.get('claimant_name', 'N/A')}**.\n\n"
                f"| Field | Value |\n"
                f"|---|---|\n"
                f"| Email | {claim.get('claimant_email', 'N/A')} |\n"
                f"| Phone | {claim.get('claimant_phone', 'N/A')} |\n"
                f"| Policy Number | {claim.get('policy_number', 'N/A')} |"
            )

        if intent == "get_claim_details" and "claim" in database_context:
            claim = database_context["claim"]

            if "status" in message_lower:
                return (
                    f"Claim **{claim.get('claim_number', 'N/A')}** is currently "
                    f"**{claim.get('status', 'N/A')}**."
                )

            if "risk" in message_lower:
                return (
                    f"Claim **{claim.get('claim_number', 'N/A')}** has a risk score of "
                    f"**{claim.get('risk_score', 'N/A')}/100** "
                    f"and risk level **{claim.get('risk_level', 'N/A')}**."
                )

            if "amount" in message_lower or "how much" in message_lower:
                return (
                    f"Claim **{claim.get('claim_number', 'N/A')}** amount is "
                    f"**${claim.get('claim_amount', 0):,.2f}**."
                )

            return self._format_database_results(database_context)

        if intent in ["find_similar_claims", "claim_statistics", "high_risk_claims"]:
            return self._format_database_results(database_context)

        if intent == "fraud_detection":
            formatted_data = self._format_database_results(database_context)

            if self.use_llm:
                prompt = f"""
User question:
{user_message}

Database evidence:
{formatted_data}

Instructions:
- Answer the user's specific question.
- Be concise.
- Do not repeat the welcome message.
- Start with a direct fraud/risk conclusion.
- Then list the strongest 2-3 evidence points.
- Use the table only as supporting evidence if useful.
- Do not invent facts.

Answer:
"""
                return self.watsonx_client.generate_response(prompt, [])

            return formatted_data

        if self.use_llm:
            return await self._generate_response_with_context(
                user_message=user_message,
                database_context=database_context
            )

        return self._format_database_results(database_context)

    async def _generate_response_with_context(
        self,
        user_message: str,
        database_context: Dict[str, Any]
    ) -> str:
        formatted_data = self._format_database_results(database_context)

        if not self.use_llm:
            return formatted_data

        prompt = f"""
User question:
{user_message}

Grounded database result:
{formatted_data}

Instructions:
- Answer the user's actual question, not a generic system description.
- Be concise and specific.
- Do not repeat the welcome message.
- Do not list all capabilities unless asked.
- Use a table only when comparing multiple claims or showing structured records.
- For simple questions, answer in 1-3 sentences.
- Do not invent data beyond the database result.
- If the data does not answer the question, say what is missing.

Answer:
"""

        return self.watsonx_client.generate_response(prompt, [])

    def _format_database_results(self, context: Dict[str, Any]) -> str:
        if "claim" in context:
            claim = context["claim"]
            return f"""
| Field | Value |
|---|---|
| Claim Number | {claim.get('claim_number', 'N/A')} |
| Claimant | {claim.get('claimant_name', 'N/A')} |
| Email | {claim.get('claimant_email', 'N/A')} |
| Phone | {claim.get('claimant_phone', 'N/A')} |
| Policy Number | {claim.get('policy_number', 'N/A')} |
| Type | {claim.get('claim_type', 'N/A')} |
| Amount | ${claim.get('claim_amount', 0):,.2f} |
| Status | {claim.get('status', 'N/A')} |
| Risk Score | {claim.get('risk_score', 'N/A')}/100 |
| Risk Level | {claim.get('risk_level', 'N/A')} |
| Incident Date | {claim.get('incident_date', 'N/A')} |
| Claim Date | {claim.get('claim_date', 'N/A')} |

**Description:** {claim.get('description', 'N/A')}
""".strip()

        if "similar_claims" in context:
            rows = [
                "| Claim Number | Amount | Risk Score | Status | Similarity |",
                "|---|---:|---:|---|---:|"
            ]

            for claim in context["similar_claims"][:5]:
                rows.append(
                    f"| {claim.get('claim_number', 'N/A')} "
                    f"| ${claim.get('claim_amount', 0):,.2f} "
                    f"| {claim.get('risk_score', 'N/A')}/100 "
                    f"| {claim.get('status', 'N/A')} "
                    f"| {claim.get('similarity_score', 0):.2%} |"
                )

            return "\n".join(rows)

        if "fraud_patterns" in context:
            rows = [
                "| Claim Number | Amount | Risk Score | Status | Similarity |",
                "|---|---:|---:|---|---:|"
            ]

            for claim in context["fraud_patterns"][:5]:
                rows.append(
                    f"| {claim.get('claim_number', 'N/A')} "
                    f"| ${claim.get('claim_amount', 0):,.2f} "
                    f"| {claim.get('risk_score', 'N/A')}/100 "
                    f"| {claim.get('status', 'N/A')} "
                    f"| {claim.get('similarity_score', 0):.2%} |"
                )

            return "Potential fraud patterns found:\n\n" + "\n".join(rows)

        if "statistics" in context:
            stats = context["statistics"]
            return f"""
| Metric | Value |
|---|---:|
| Total Claims | {stats.get('total_claims', 0):,} |
| Total Amount | ${stats.get('total_amount', 0):,.2f} |
| Average Amount | ${stats.get('average_amount', 0):,.2f} |
| Approved Claims | {stats.get('approved_count', 0):,} |
| Under Review | {stats.get('under_review_count', 0):,} |
| Escalated | {stats.get('escalated_count', 0):,} |
| Rejected | {stats.get('rejected_count', 0):,} |
| Low Risk | {stats.get('low_risk_count', 0):,} |
| Medium Risk | {stats.get('medium_risk_count', 0):,} |
| High Risk | {stats.get('high_risk_count', 0):,} |
| Average Risk Score | {stats.get('average_risk_score', 0):.1f}/100 |
""".strip()

        if "high_risk_claims" in context:
            rows = [
                "| Claim Number | Claimant | Amount | Risk Score | Status | Created |",
                "|---|---|---:|---:|---|---|"
            ]

            for claim in context["high_risk_claims"][:10]:
                rows.append(
                    f"| {claim.get('claim_number', 'N/A')} "
                    f"| {claim.get('claimant_name', 'N/A')} "
                    f"| ${claim.get('claim_amount', 0):,.2f} "
                    f"| {claim.get('risk_score', 'N/A')}/100 "
                    f"| {claim.get('status', 'N/A')} "
                    f"| {claim.get('created_at', 'N/A')} |"
                )

            return "\n".join(rows)

        return "No specific database data found."

    def _detect_intent(self, message: str) -> str:
        message_lower = message.lower()

        if re.search(r'claim\s*#?\s*\d+|clm-\d+-\d+', message_lower):
            if "policyholder" in message_lower or "policy holder" in message_lower:
                return "find_policyholder"
            return "get_claim_details"

        if any(word in message_lower for word in ["similar", "like", "resembles", "comparable"]):
            return "find_similar_claims"

        if any(word in message_lower for word in ["fraud", "suspicious", "fraudulent"]):
            return "fraud_detection"

        if any(word in message_lower for word in ["statistics", "stats", "average", "total", "count"]):
            return "claim_statistics"

        if "high risk" in message_lower or "escalated" in message_lower:
            return "high_risk_claims"

        return "general"

    def _extract_claim_number(self, message: str) -> Optional[str]:
        patterns = [
            r'claim\s*#?\s*(\d+)',
            r'(clm-\d+-\d+)',
            r'#(\d+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, message.lower())
            if match:
                claim_num = match.group(1)

                if claim_num.isdigit():
                    return f"CLM-2026-{int(claim_num):06d}"

                return claim_num.upper()

        return None

    async def _handle_general_query(self, message: str) -> str:
        if self.use_llm:
            prompt = f"""
User question:
{message}

Instructions:
- Answer only this question.
- Be concise.
- Do not repeat the welcome message.
- Do not list all capabilities unless asked.
- If the question is vague, ask one short clarifying question.
"""
            return self.watsonx_client.generate_response(prompt, [])

        return "Please ask about a claim number, similar claims, fraud patterns, high-risk claims, or claim statistics."


@cl.on_chat_start
async def start():
    """Initialize session and display welcome message once."""

    agent = AdjusterAgent()
    cl.user_session.set("agent", agent)

    await cl.Message(
        content="""
# 👋 Welcome to the Claims Intelligence Assistant

Ask me about a claim, policyholder, similar claims, fraud patterns, high-risk cases, or claim statistics.

Examples:
- `Who is the policyholder for claim #CLM-2026-000001?`
- `Show me claim CLM-2026-000001`
- `Find similar claims numbers: car accident on highway`
- `Find fraud patterns similar to: staged accident with fake injuries`
- `Show me high-risk claims`
- `Show me claim statistics`
""".strip()
    ).send()


@cl.on_message
async def main(message: cl.Message):
    """Handle incoming user messages."""

    agent = cl.user_session.get("agent")

    if not agent:
        await cl.Message(content="❌ Session error. Please refresh the page.").send()
        return

    try:
        response = await agent.process_query(message.content)
    except Exception as e:
        logger.error("query_processing_failed", error=str(e))
        response = f"❌ Error processing your query: {str(e)}"

    await cl.Message(content=response).send()


@cl.on_chat_end
async def end():
    """Clean up when chat ends."""

    agent = cl.user_session.get("agent")

    if agent and agent.db_client:
        agent.db_client.close()

    logger.info("chat_session_ended")


if __name__ == "__main__":
    pass