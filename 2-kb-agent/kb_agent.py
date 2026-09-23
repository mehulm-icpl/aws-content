from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

# Initialize the Bedrock model (Anthropic Claude Sonnet 4.5)
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    temperature=0.3
)

# AgentCore endpoint
@app.entrypoint
def strands_agent_bedrock(payload):
    # Create the agent inside the entrypoint — each request gets its own instance
    # This allows multiple users to invoke the agent concurrently without conflicts
    agent = Agent(
        model=model,
        tools=[],
        system_prompt="You are a helpful assistant."
    )

    try:
        user_input = payload.get("prompt")
        history = payload.get("history", [])

        # Build context from conversation history
        if history:
            context = chr(10).join([f"{'User' if msg.get('role')=='user' else 'Assistant'}: {msg.get('content','')}" for msg in history])
            full_prompt = f"Previous conversation:{chr(10)}{context}{chr(10)}{chr(10)}New user message: {user_input}"
        else:
            full_prompt = user_input

        response = agent(full_prompt)

        # Collect all content blocks from the response
        content_blocks = response.message.get('content', [])
        result_parts = []

        for block in content_blocks:
            if isinstance(block, dict):
                if 'text' in block:
                    result_parts.append(block['text'])
            elif isinstance(block, str):
                result_parts.append(block)

        return chr(10).join(result_parts) if result_parts else "No response generated."
    finally:
        print("[Agent] Request completed")

if __name__ == "__main__":
    app.run()
