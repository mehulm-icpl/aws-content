import boto3
import json
import uuid
from boto3.session import Session


# Replace with your agent ARN (example: arn:aws:bedrock-agentcore:us-west-2:XXXXXXXXXXXX:runtime/agent-XXXXXXXXXX)
agent_arn = 'arn:aws:bedrock-agentcore:us-west-2:685341797369:runtime/agent-wj4qLrADLM'

# Replace with your test prompt (example: '1) Calculate 10 × 100 + 20 + √(81)? 2) What regions is AWS AgentCore available in? 3) What is the weather in NYC today? Respond with a summary of answers to all three questions even if you answered it before.')
prompt = """1) Calculate 10 × 100 + 20 + √(81)? 
2) What regions is AWS AgentCore available in? 
3) what is the temperature in ahmedabad?
Respond with a summary of answers to all three questions even if you answered it before."""


# Get the current AWS region
boto_session = Session()
region = boto_session.region_name

# Initialize AgentCore client
agentcore_client = boto3.client('bedrock-agentcore', region_name=region)

def generate_session_id():
    """Generate a unique session ID (33+ characters required)"""
    return str(uuid.uuid4()).replace('-', '') + str(uuid.uuid4()).replace('-', '')[:5]

# Invoke the agent
response = agentcore_client.invoke_agent_runtime(
    agentRuntimeArn=agent_arn,
    qualifier="DEFAULT",
    runtimeSessionId=generate_session_id(),
    payload=json.dumps({"prompt": prompt})
)

# Process response events
try:
    response_body = response['response'].read()
    response_data = json.loads(response_body)
    print("Agent Response:", response_data)
except json.JSONDecodeError:
    # If not JSON, treat as plain text
    print(response_text)