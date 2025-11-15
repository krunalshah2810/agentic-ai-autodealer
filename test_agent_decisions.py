import pandas as pd
from agents.bedrock_agent import BedrockAgentCore
import json

# Load data
inventory = pd.read_csv('data/inventory.csv')
competitors = pd.read_csv('data/competitors.csv')
inquiries = pd.read_csv('data/customer_inquiries.csv')

# Initialize agent
agent = BedrockAgentCore()

print("🧠 Testing Agent Decision-Making...\n")
print(f"📊 Data loaded:")
print(f"   - Inventory: {len(inventory)} vehicles")
print(f"   - Competitors: {len(competitors)} listings")
print(f"   - Inquiries: {len(inquiries)} inquiries\n")

# Get decisions
print("🤖 Asking agent for decisions...\n")
decisions = agent.agent_decision_loop(inventory, competitors, inquiries)

if decisions:
    print("✅ Agent returned decisions!\n")
    print(json.dumps(decisions, indent=2))
    
    # Check what was returned
    print("\n📋 Decision Summary:")
    for key, value in decisions.items():
        if isinstance(value, list):
            print(f"   {key}: {len(value)} items")
        else:
            print(f"   {key}: {value}")
else:
    print("❌ No decisions returned!")
    print("\nPossible issues:")
    print("1. AWS Bedrock credentials not configured")
    print("2. Model not returning valid JSON")
    print("3. API rate limiting")