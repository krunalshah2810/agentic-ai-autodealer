import boto3
import json
from dotenv import load_dotenv
import os

load_dotenv()
print("DEBUG MODEL ID =", os.getenv("BEDROCK_MODEL_ID"))

# Initialize Bedrock client
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)

def test_claude():
    """Test AWS Bedrock connection with Claude"""
    
    prompt = "You are a car dealership AI agent. Say hello and confirm you're ready to help sell cars!"
    
    # Bedrock request format for Claude
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 500,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    try:
        response = bedrock_runtime.invoke_model(
            modelId=os.getenv('BEDROCK_MODEL_ID'),
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        assistant_message = response_body['content'][0]['text']
        
        print("✅ Bedrock Connection Successful!")
        print(f"\nClaude says:\n{assistant_message}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_claude()