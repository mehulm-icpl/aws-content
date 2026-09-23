import boto3

# Configuration - Replace with your values
parameters = {
    "team_name": "<team name>",
    "application_name": "<application name>",
    "application_description": "<application description>",
    "application_examples": "<example question 1>, <example question 2>",
    "agent_arn": "<agent arn>",
    "introductory_message": "<introductory message>"
    }

def clean_value(value: str) -> str:
    """Strip < and > characters from placeholder values like <team name> → team name."""
    return value.strip().strip('<>').strip()

# Create SSM client and store parameters
ssm_client = boto3.client('ssm')

for name, value in parameters.items():
    cleaned = clean_value(value)
    try:
        ssm_client.put_parameter(Name=name, Value=cleaned if cleaned else " ", Type="String", Overwrite=True)
        print(f"💾 Successfully stored parameter: {name} = {cleaned}")
    except Exception as e:
        print(f"⚠️ Error storing {name} parameter: {e}")
