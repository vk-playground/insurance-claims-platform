"""Watsonx.ai LLM Client for Conversational AI."""
import os
from typing import List, Dict, Any, Optional
from ibm_watsonx_ai.foundation_models import Model
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai import Credentials
import structlog

logger = structlog.get_logger()


class WatsonxClient:
    """Client for IBM watsonx.ai LLM integration."""
    
    def __init__(
        self,
        api_key: str,
        project_id: str,
        url: str = "https://ca-tor.ml.cloud.ibm.com",
        model_id: str = "meta-llama/llama-3-3-70b-instruct"
    ):
        """
        Initialize Watsonx.ai client.
        
        Args:
            api_key: IBM Cloud API key
            project_id: Watsonx.ai project ID
            url: Watsonx.ai service URL
            model_id: Model to use for generation
        """
        self.api_key = api_key
        self.project_id = project_id
        self.url = url
        self.model_id = model_id
        
        # Initialize credentials
        self.credentials = Credentials(
            url=url,
            api_key=api_key
        )
        
        # Initialize model with parameters
        self.parameters = {
            GenParams.DECODING_METHOD: "greedy",
            GenParams.MAX_NEW_TOKENS: 1000,
            GenParams.MIN_NEW_TOKENS: 1,
            GenParams.TEMPERATURE: 0.7,
            GenParams.TOP_K: 50,
            GenParams.TOP_P: 1,
            GenParams.REPETITION_PENALTY: 1.1
        }
        
        self.model = Model(
            model_id=model_id,
            params=self.parameters,
            credentials=self.credentials,
            project_id=project_id
        )
        
        logger.info("watsonx_client_initialized", model_id=model_id)
    
    def generate_response(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate a response using watsonx.ai.
        
        Args:
            prompt: User's input prompt
            conversation_history: Previous conversation messages
            
        Returns:
            Generated response text
        """
        try:
            # Build full prompt with history
            full_prompt = self._build_prompt(prompt, conversation_history)
            
            # Generate response
            response = self.model.generate_text(prompt=full_prompt)
            
            logger.info("watsonx_response_generated", prompt_length=len(full_prompt))
            
            return response.strip()
            
        except Exception as e:
            logger.error("watsonx_generation_failed", error=str(e))
            raise
    
    def _build_prompt(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Build a complete prompt with system instructions and conversation history.
        
        Args:
            user_message: Current user message
            conversation_history: Previous conversation messages
            
        Returns:
            Formatted prompt string
        """
        # System prompt for the insurance adjuster agent
        system_prompt = """You are an AI assistant for insurance claim adjusters. Your role is to help adjusters:

1. Query and analyze insurance claims data
2. Find similar claims using semantic search
3. Detect potential fraud patterns
4. Provide claim statistics and insights
5. Identify high-risk claims

You have access to a database of insurance claims with the following information:
- Claim numbers (format: CLM-2026-XXXXXX)
- Policyholder details (name, email, phone, policy number)
- Claim details (type, amount, status, risk score, description)
- Dates (incident date, claim date, created date)

When users ask questions:
- Be professional and concise
- Provide specific data when available
- Suggest relevant follow-up queries
- Explain your reasoning when detecting fraud or high-risk patterns
- Use markdown formatting for clarity

Available query types:
- Claim details: "Show me claim #123" or "Get details for CLM-2026-000001"
- Policyholder info: "Who is the policyholder for claim #123?"
- Similar claims: "Find claims similar to: car accident on highway"
- Fraud detection: "Check for fraud patterns like: staged accident"
- Statistics: "Show me claim statistics" or "What's the average claim amount?"
- High-risk claims: "List high-risk claims" or "Show escalated cases"

Always maintain context from previous messages in the conversation."""

        # Build conversation history
        prompt_parts = [system_prompt, "\n\n"]
        
        if conversation_history:
            for msg in conversation_history[-6:]:  # Keep last 6 messages for context
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "user":
                    prompt_parts.append(f"User: {content}\n\n")
                elif role == "assistant":
                    prompt_parts.append(f"Assistant: {content}\n\n")
        
        # Add current user message
        prompt_parts.append(f"User: {user_message}\n\nAssistant:")
        
        return "".join(prompt_parts)
    
    def generate_with_context(
        self,
        user_message: str,
        database_context: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate response with additional database context.
        
        Args:
            user_message: User's input message
            database_context: Relevant data from database queries
            conversation_history: Previous conversation messages
            
        Returns:
            Generated response with context
        """
        # Build enhanced prompt with database context
        context_prompt = self._build_context_prompt(user_message, database_context)
        
        # Generate response
        return self.generate_response(context_prompt, conversation_history)
    
    def _build_context_prompt(
        self,
        user_message: str,
        database_context: Dict[str, Any]
    ) -> str:
        """
        Build prompt with database context.
        
        Args:
            user_message: User's message
            database_context: Database query results
            
        Returns:
            Enhanced prompt with context
        """
        context_parts = [f"User Query: {user_message}\n\n"]
        
        # Add database context
        if database_context:
            context_parts.append("Database Context:\n")
            
            if "claim" in database_context:
                claim = database_context["claim"]
                context_parts.append(f"- Claim Number: {claim.get('claim_number')}\n")
                context_parts.append(f"- Claimant: {claim.get('claimant_name')}\n")
                context_parts.append(f"- Amount: ${claim.get('claim_amount', 0):,.2f}\n")
                context_parts.append(f"- Status: {claim.get('status')}\n")
                context_parts.append(f"- Risk Score: {claim.get('risk_score')}/100\n")
            
            if "similar_claims" in database_context:
                similar = database_context["similar_claims"]
                context_parts.append(f"\n- Found {len(similar)} similar claims\n")
            
            if "statistics" in database_context:
                stats = database_context["statistics"]
                context_parts.append(f"\n- Total Claims: {stats.get('total_claims', 0)}\n")
                context_parts.append(f"- Average Amount: ${stats.get('average_amount', 0):,.2f}\n")
            
            context_parts.append("\n")
        
        context_parts.append("Please provide a helpful response based on this information.")
        
        return "".join(context_parts)
    
    def extract_intent(self, user_message: str) -> Dict[str, Any]:
        """
        Use LLM to extract intent and entities from user message.
        
        Args:
            user_message: User's input message
            
        Returns:
            Dictionary with intent and extracted entities
        """
        intent_prompt = f"""Analyze this insurance claim query and extract:
1. Intent (one of: claim_details, policyholder_info, similar_claims, fraud_detection, statistics, high_risk_claims, general)
2. Entities (claim numbers, amounts, keywords)

Query: {user_message}

Respond in JSON format:
{{
    "intent": "intent_name",
    "entities": {{
        "claim_number": "CLM-2026-000001",
        "keywords": ["keyword1", "keyword2"]
    }}
}}"""

        try:
            response = self.model.generate_text(prompt=intent_prompt)
            
            # Parse JSON response
            import json
            intent_data = json.loads(response.strip())
            
            logger.info("intent_extracted", intent=intent_data.get("intent"))
            
            return intent_data
            
        except Exception as e:
            logger.error("intent_extraction_failed", error=str(e))
            # Fallback to general intent
            return {
                "intent": "general",
                "entities": {}
            }
    
    def summarize_conversation(
        self,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        Generate a summary of the conversation.
        
        Args:
            conversation_history: List of conversation messages
            
        Returns:
            Summary text
        """
        if not conversation_history:
            return "No conversation history."
        
        # Build conversation text
        conv_text = []
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            conv_text.append(f"{role.title()}: {content}")
        
        summary_prompt = f"""Summarize this conversation between a user and an insurance claims assistant:

{chr(10).join(conv_text)}

Provide a brief summary of:
1. What the user asked about
2. Key information provided
3. Any actions taken or recommendations made"""

        try:
            summary = self.model.generate_text(prompt=summary_prompt)
            return summary.strip()
        except Exception as e:
            logger.error("summarization_failed", error=str(e))
            return "Unable to generate summary."


# Singleton instance
_watsonx_client = None


def get_watsonx_client() -> WatsonxClient:
    """Get or create singleton watsonx client."""
    global _watsonx_client
    
    if _watsonx_client is None:
        api_key = os.getenv("WATSONX_API_KEY")
        project_id = os.getenv("WATSONX_PROJECT_ID")
        url = os.getenv("WATSONX_URL", "https://ca-tor.ml.cloud.ibm.com")
        model_id = os.getenv("WATSONX_MODEL_ID", "meta-llama/llama-3-3-70b-instruct")
        
        if not api_key or not project_id:
            raise ValueError("WATSONX_API_KEY and WATSONX_PROJECT_ID must be set")
        
        _watsonx_client = WatsonxClient(
            api_key=api_key,
            project_id=project_id,
            url=url,
            model_id=model_id
        )
    
    return _watsonx_client

# Made with Bob
