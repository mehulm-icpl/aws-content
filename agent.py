from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands_tools import calculator, http_request
from mcp import stdio_client, StdioServerParameters
from strands.tools.mcp import MCPClient

app = BedrockAgentCoreApp()

# Initialize the Bedrock model (Anthropic Claude Sonnet 4.5)
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    temperature=0.3
)

# Create MCP client for AWS documentation
mcp_client = MCPClient(lambda: stdio_client(
    StdioServerParameters(
        command="python",
        args=["-m", "awslabs.aws_documentation_mcp_server.server"]
    )
))

# Create the basic agent
agent = Agent(
    model=model,
    tools=[calculator, mcp_client, http_request],
    system_prompt="""You're a helpful assistant with access to tools.
    When asked for weather information:
    1. Make HTTP requests to the National Weather Service API
    2. Process and display weather forecast data
    3. Provide weather information for locations in the United States
    When retrieving weather information:
    1. First get the coordinates or grid information using https://api.weather.gov/points/{latitude},{longitude} or https://api.weather.gov/points/{zipcode}
    2. Then use the returned forecast URL to get the actual forecast
    When displaying responses:
    - Format weather data in a human-readable way
    - Highlight important information like temperature, precipitation, and alerts
    - Handle errors appropriately
    - Convert technical terms to user-friendly language
    Always explain the weather conditions clearly and provide context for the forecast.
    When asked mathematical questions:
    1. use calculator tool
    When displaying responses:
    - Format calculation data in a human-readable way
    - Handle errors appropriately
    When asked about AWS:
    1. look at AWS documentation using MCP client
    When displaying responses:
    - Format calculation data in a human-readable way
    - Handle errors appropriately
    - Convert technical terms to user-friendly language
    """
)

# AgentCore endpoint
@app.entrypoint
def strands_agent_bedrock(payload):
    """
    Invoke the agent with a payload
    """
    user_input = payload.get("prompt")
    print("User input:", user_input)
    response = agent(user_input)
    return response.message['content'][0]['text']

if __name__ == "__main__":
    app.run()