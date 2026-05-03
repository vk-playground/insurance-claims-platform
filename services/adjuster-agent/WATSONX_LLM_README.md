# Watsonx.ai LLM Integration for Adjuster Agent

## Overview

The Adjuster Agent now features **true conversational AI** powered by IBM Watsonx.ai, replacing the previous pattern-based intent detection with natural language understanding capabilities.

## Architecture

### Before: Pattern-Based (Regex)
```
User Message → Regex Pattern Matching → Hardcoded Handler → Response
```

### After: LLM-Powered Conversational AI
```
User Message → Watsonx.ai LLM → Intent Extraction → Database Context → LLM Response Generation → Conversational Response
```

## Key Features

### 1. Natural Language Understanding
- **Context-Aware**: Understands follow-up questions without repeating context
- **Flexible Queries**: No need for specific keywords or patterns
- **Intent Detection**: Uses LLM to extract intent and entities from natural language

### 2. Conversational Memory
- Maintains conversation history (last 6 messages)
- Understands references like "that claim", "the policyholder", etc.
- Provides contextual responses based on previous interactions

### 3. Database-Aware Responses
- Queries CockroachDB for relevant data
- Formats database results for LLM context
- Generates explanations and insights from data

### 4. Hybrid Approach
- **Primary**: LLM-powered conversational AI (when watsonx.ai is available)
- **Fallback**: Pattern-based processing (if LLM initialization fails)

## Configuration

### Environment Variables

Add to `.env`:
```bash
# IBM Watsonx.ai Configuration
WATSONX_API_KEY=your_api_key_here
WATSONX_PROJECT_ID=your_project_id_here
WATSONX_URL=https://ca-tor.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-13b-chat-v2
```

### Supported Models

- **ibm/granite-13b-chat-v2** (default) - Balanced performance and quality
- **ibm/granite-20b-multilingual** - Multilingual support
- **meta-llama/llama-2-70b-chat** - Higher quality responses
- **mistralai/mixtral-8x7b-instruct-v01** - Fast inference

## Usage Examples

### Example 1: Natural Follow-up Questions
```
User: "Show me claim #123"
Agent: [Shows claim details]

User: "What about the policyholder?"
Agent: [Understands "the policyholder" refers to claim #123]

User: "Are there similar claims?"
Agent: [Finds similar claims to #123]
```

### Example 2: Conversational Fraud Detection
```
User: "I'm concerned about a claim that looks suspicious - staged car accident with exaggerated injuries"
Agent: [Uses LLM to understand context, searches for similar high-risk claims, explains patterns]

User: "What makes these risky?"
Agent: [Provides detailed explanation based on risk scores and patterns]
```

### Example 3: Data Insights
```
User: "Show me statistics"
Agent: [Retrieves stats from database]

User: "Why are so many claims escalated?"
Agent: [LLM analyzes data and provides insights]
```

## Implementation Details

### 1. Watsonx Client (`watsonx_client.py`)

```python
class WatsonxClient:
    def generate_response(prompt, conversation_history)
    def extract_intent(user_message)
    def generate_with_context(user_message, database_context)
    def summarize_conversation(conversation_history)
```

### 2. Enhanced Adjuster Agent (`app.py`)

```python
class AdjusterAgent:
    async def _process_with_llm(user_message)
    async def _gather_database_context(intent, entities, user_message)
    async def _generate_llm_response_with_context(user_message, database_context)
    async def _process_with_patterns(user_message)  # Fallback
```

### 3. Processing Flow

1. **User Input** → Store in conversation history
2. **Intent Detection** → LLM extracts intent and entities
3. **Context Gathering** → Query database based on intent
4. **Response Generation** → LLM generates response with database context
5. **Response Delivery** → Send formatted response to user

## System Prompt

The LLM is configured with a comprehensive system prompt that defines:
- Role as insurance claims adjuster assistant
- Available data and query types
- Response formatting guidelines
- Context awareness requirements

## Performance Considerations

### Response Times
- **LLM Generation**: 2-5 seconds (depends on model and prompt length)
- **Database Queries**: <1 second
- **Total Response Time**: 3-6 seconds

### Token Usage
- **System Prompt**: ~400 tokens
- **Conversation History**: ~100-300 tokens (last 6 messages)
- **Database Context**: ~200-500 tokens
- **Response**: ~200-800 tokens
- **Total per Request**: ~900-2000 tokens

### Cost Optimization
- Conversation history limited to last 6 messages
- Database context formatted concisely
- Greedy decoding for consistent responses
- Max tokens: 1000 per response

## Error Handling

### LLM Initialization Failure
```python
try:
    self.watsonx_client = get_watsonx_client()
    self.use_llm = True
except Exception as e:
    logger.warning("watsonx_client_disabled", error=str(e))
    self.use_llm = False  # Falls back to pattern-based
```

### Generation Errors
- Catches exceptions during LLM generation
- Returns user-friendly error messages
- Logs errors for debugging
- Maintains conversation history

## Testing

### Manual Testing
```bash
# Start the agent
cd insurance-claims-platform/services/adjuster-agent
chainlit run app.py

# Test conversational queries:
1. "Show me claim #1"
2. "What about the policyholder?" (follow-up)
3. "Find similar claims"
4. "Why is this claim risky?" (explanation)
```

### Verification Checklist
- [ ] LLM initializes successfully
- [ ] Intent detection works for various queries
- [ ] Database context is gathered correctly
- [ ] Responses are conversational and contextual
- [ ] Follow-up questions work properly
- [ ] Error handling works when LLM fails
- [ ] Fallback to pattern-based works

## Troubleshooting

### Issue: "watsonx_client_disabled"
**Cause**: Missing or invalid watsonx.ai credentials
**Solution**: 
1. Check `.env` file has correct credentials
2. Verify API key is valid
3. Ensure project ID is correct
4. Check network connectivity to watsonx.ai

### Issue: Slow Responses
**Cause**: Large conversation history or complex queries
**Solution**:
1. Conversation history auto-limited to 6 messages
2. Use more concise database context
3. Consider faster model (granite-13b vs llama-70b)

### Issue: Generic Responses
**Cause**: Insufficient database context
**Solution**:
1. Check database queries are returning data
2. Verify embeddings are populated
3. Review context formatting in logs

## Comparison: Pattern-Based vs LLM

| Feature | Pattern-Based | LLM-Powered |
|---------|--------------|-------------|
| Natural Language | ❌ Limited | ✅ Full support |
| Context Awareness | ❌ None | ✅ Full history |
| Follow-up Questions | ❌ No | ✅ Yes |
| Explanations | ❌ Hardcoded | ✅ Generated |
| Flexibility | ❌ Fixed patterns | ✅ Adaptive |
| Response Time | ✅ <1s | ⚠️ 3-6s |
| Cost | ✅ Free | ⚠️ API costs |
| Reliability | ✅ 100% | ⚠️ 95-99% |

## Future Enhancements

### Planned Features
1. **Streaming Responses**: Real-time token streaming for faster perceived response
2. **Multi-turn Reasoning**: Chain-of-thought for complex queries
3. **Tool Use**: LLM decides which database queries to run
4. **Conversation Summarization**: Auto-summarize long conversations
5. **Personalization**: Learn user preferences over time

### Advanced Capabilities
- **RAG (Retrieval Augmented Generation)**: Use vector search for context
- **Function Calling**: LLM triggers specific database operations
- **Multi-modal**: Support for claim images and documents
- **Batch Processing**: Analyze multiple claims simultaneously

## References

- [IBM Watsonx.ai Documentation](https://www.ibm.com/docs/en/watsonx-as-a-service)
- [Granite Models](https://www.ibm.com/granite)
- [Chainlit Documentation](https://docs.chainlit.io/)
- [LangChain Integration](https://python.langchain.com/docs/integrations/llms/ibm_watsonx)

## Support

For issues or questions:
1. Check logs: `LOG_LEVEL=DEBUG` in `.env`
2. Review conversation history in Chainlit UI
3. Test with pattern-based fallback: Remove watsonx credentials temporarily
4. Check watsonx.ai service status

---

**Made with Bob** 🤖