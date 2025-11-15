import boto3
import json
import os
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd
import json

load_dotenv()

class BedrockAgentCore:
    """
    Core agentic AI system using AWS Bedrock Claude
    This is the "brain" that makes autonomous decisions
    """
    
    def __init__(self):
        self.bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.model_id = os.getenv('BEDROCK_MODEL_ID')
        self.dealer_name = os.getenv('DEALER_NAME', 'Premium Auto Sales')
        self.min_margin = float(os.getenv('MIN_PROFIT_MARGIN', 0.05))
        self.max_adjustment = float(os.getenv('MAX_PRICE_ADJUSTMENT', 0.15))
        
    def invoke_claude(self, messages, max_tokens=4000, temperature=0.7):
        """Call AWS Bedrock Claude model"""
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        try:
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            print(f"❌ Bedrock error: {e}")
            return None
    
    def agent_decision_loop(self, inventory_df, competitor_df, inquiries_df):
        """
        🤖 THE MAIN AGENTIC LOOP
        """
        
        # Prepare context for Claude
        context = self._prepare_decision_context(inventory_df, competitor_df, inquiries_df)
        
        # Ask Claude to make decisions
        prompt = f"""You are an autonomous AI agent managing a car dealership called {self.dealer_name}.

    {context}

    YOUR TASK:
    Analyze the aged vehicles and customer inquiries above and make specific recommendations.

    CRITICAL RULES:
    1. You MUST use EXACT VINs and stock numbers from the data I provided above
    2. You MUST use EXACT inquiry_ids from the customer inquiries above
    3. Do NOT invent or generate fake IDs
    4. Only recommend price changes that maintain minimum {self.min_margin*100}% profit margin
    5. Maximum price change: ±{self.max_adjustment*100}%

    DECISION FRAMEWORK:
    - Vehicles > 60 days: Recommend 5-10% price reduction (if margin allows)
    - Hot leads: Draft immediate response
    - Price shoppers: Provide value justification

    Respond with ONLY this JSON structure (no markdown, no explanations):

    {{
    "analysis_summary": "2-3 sentence summary of current situation",
    "price_adjustments": [
        {{
        "vin": "EXACT VIN from above data",
        "stock_number": "EXACT stock_number from above",
        "current_price": current price as number,
        "recommended_price": new price as number,
        "reason": "brief explanation",
        "confidence": 0.85,
        "urgency": "high"
        }}
    ],
    "customer_responses": [
        {{
        "inquiry_id": "EXACT inquiry_id from above",
        "customer_name": "name from data",
        "response_subject": "subject line",
        "response_body": "email content",
        "offer_price": null,
        "strategy": "approach explanation"
        }}
    ],
    "social_media_posts": [],
    "urgent_alerts": []
    }}

    Generate 3-5 price adjustments for the most aged vehicles and 2-3 customer responses.
    Remember: Use ONLY the exact VINs and IDs from the data above."""

        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = self.invoke_claude(messages, max_tokens=4000, temperature=0.7)
            
            if not response:
                print("⚠️ No response from Claude")
                return self._generate_fallback_decisions(inventory_df, inquiries_df)
            
            # Try to parse JSON
            try:
                json_text = self._extract_json(response)
                decisions = json.loads(json_text)
                
                # Validate that VINs exist
                valid_vins = set(inventory_df['vin'].values)
                valid_decisions = self._validate_decisions(decisions, valid_vins, set(inquiries_df['inquiry_id'].values))
                
                print("✅ Successfully parsed and validated JSON decisions")
                return valid_decisions
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing failed: {e}")
                return self._generate_fallback_decisions(inventory_df, inquiries_df)
        
        except Exception as e:
            print(f"❌ Error in agent loop: {e}")
            return self._generate_fallback_decisions(inventory_df, inquiries_df)

    def _validate_decisions(self, decisions, valid_vins, valid_inquiry_ids):
        """Validate and filter decisions to only include real IDs"""
        
        # Filter price adjustments to only valid VINs
        if 'price_adjustments' in decisions:
            original_count = len(decisions['price_adjustments'])
            decisions['price_adjustments'] = [
                adj for adj in decisions['price_adjustments'] 
                if adj.get('vin') in valid_vins
            ]
            filtered_count = original_count - len(decisions['price_adjustments'])
            if filtered_count > 0:
                print(f"⚠️ Filtered out {filtered_count} price adjustments with invalid VINs")
        
        # Filter customer responses to only valid inquiry IDs
        if 'customer_responses' in decisions:
            original_count = len(decisions['customer_responses'])
            decisions['customer_responses'] = [
                resp for resp in decisions['customer_responses']
                if resp.get('inquiry_id') in valid_inquiry_ids
            ]
            filtered_count = original_count - len(decisions['customer_responses'])
            if filtered_count > 0:
                print(f"⚠️ Filtered out {filtered_count} responses with invalid inquiry IDs")
        
        return decisions
    
    def _prepare_decision_context(self, inventory_df, competitor_df, inquiries_df):
        """Prepare data context for Claude"""
        
        # Inventory analysis
        aged_inventory = inventory_df[inventory_df['days_in_inventory'] > 60]
        hot_inventory = inventory_df[inventory_df['days_in_inventory'] < 30]
        
        # Competitor pricing
        comp_summary = competitor_df.groupby(['make', 'model'])['price'].agg(['mean', 'min', 'max']).reset_index()
        
        # New inquiries
        new_inquiries = inquiries_df[inquiries_df['status'] == 'new']
        
        # IMPORTANT: Format inventory data clearly for Claude
        aged_for_context = aged_inventory.head(10)[
            ['vin', 'stock_number', 'year', 'make', 'model', 'current_price', 'cost', 'days_in_inventory']
        ].to_dict('records')
        
        inquiries_for_context = new_inquiries.head(10)[
            ['inquiry_id', 'customer_name', 'customer_type', 'message', 'stock_number', 'vin']
        ].to_dict('records')
        
        context = f"""
    INVENTORY OVERVIEW:
    - Total vehicles: {len(inventory_df)}
    - Aged inventory (60+ days): {len(aged_inventory)}
    - Fresh inventory (< 30 days): {len(hot_inventory)}
    - Total value: ${inventory_df['current_price'].sum():,.2f}
    - Average days in stock: {inventory_df['days_in_inventory'].mean():.1f}

    TOP AGED VEHICLES (MUST USE EXACT VINs & STOCK NUMBERS):
    {json.dumps(aged_for_context, indent=2)}

    CUSTOMER INQUIRIES (MUST USE EXACT inquiry_id):
    {json.dumps(inquiries_for_context, indent=2)}

    CRITICAL: When making decisions, you MUST use the EXACT VINs, stock_numbers, and inquiry_ids from above.
    Do not generate fake IDs - only use the real ones I've provided.
    """
    
        return context
    
    def _extract_json(self, text):
        """Extract JSON from markdown or mixed text"""
        # Remove markdown code blocks if present
        text = text.replace('```json', '').replace('```', '').strip()
        
        # Find JSON object
        start = text.find('{')
        end = text.rfind('}') + 1
        
        if start != -1 and end > start:
            return text[start:end]
        
        return text
    
    def generate_vehicle_description(self, vehicle):
        """Generate compelling marketing copy for a vehicle"""
        
        prompt = f"""Write a compelling 150-word vehicle description for our dealership listing.

        VEHICLE DETAILS:
        - Year: {vehicle['year']}
        - Make: {vehicle['make']}
        - Model: {vehicle['model']}
        - Trim: {vehicle.get('trim', 'Standard')}
        - Mileage: {vehicle['mileage']:,} miles
        - Color: {vehicle['color']}
        - Condition: {vehicle['condition']}
        - Price: ${vehicle['current_price']:,.2f}

        WRITING STYLE:
        - Enthusiastic but professional
        - Highlight value and key features
        - Create emotional connection
        - Include call-to-action
        - SEO-friendly

        Write ONLY the description, no preamble."""

        messages = [{"role": "user", "content": prompt}]
        return self.invoke_claude(messages, max_tokens=500, temperature=0.8)
    
    def negotiate_with_customer(self, inquiry, vehicle, competitor_avg_price):
        """Generate personalized negotiation response"""
        
        # Calculate our position
        margin = ((vehicle['current_price'] - vehicle['cost']) / vehicle['cost']) * 100
        vs_market = ((vehicle['current_price'] - competitor_avg_price) / competitor_avg_price) * 100
        
        prompt = f"""You are a skilled car sales negotiator. Draft a response to this customer inquiry.

        CUSTOMER INQUIRY:
        From: {inquiry['customer_name']} ({inquiry['customer_email']})
        Type: {inquiry['customer_type']}
        Message: "{inquiry['message']}"
        Budget: ${inquiry.get('budget_max', 'not specified')}
        Needs financing: {inquiry.get('financing_needed', 'unknown')}

        VEHICLE DETAILS:
        {vehicle['year']} {vehicle['make']} {vehicle['model']} {vehicle.get('trim', '')}
        Our price: ${vehicle['current_price']:,.2f}
        Our cost: ${vehicle['cost']:,.2f}
        Current margin: {margin:.1f}%
        Days in stock: {vehicle['days_in_inventory']}
        Market average: ${competitor_avg_price:,.2f}
        Our position vs market: {vs_market:+.1f}%

        NEGOTIATION CONSTRAINTS:
        - Minimum acceptable price: ${vehicle['cost'] * (1 + self.min_margin):,.2f} ({self.min_margin*100}% margin)
        - Maximum discount: {self.max_adjustment*100}%
        - Must remain competitive but profitable

        INSTRUCTIONS:
        1. Address customer by name
        2. Acknowledge their message/concern
        3. Provide value justification (features, condition, market position)
        4. Make a strategic counteroffer if they're negotiating
        5. Create urgency without being pushy
        6. Include clear next steps
        7. Professional, friendly tone

        Respond with JSON:
        {{
        "email_subject": "subject line",
        "email_body": "full email content",
        "recommended_offer_price": 12345,
        "negotiation_strategy": "explanation of approach",
        "probability_of_close": 0.75
        }}"""

        messages = [{"role": "user", "content": prompt}]
        response = self.invoke_claude(messages, max_tokens=1000, temperature=0.7)
        
        if response:
            try:
                return json.loads(self._extract_json(response))
            except:
                return {"email_body": response, "error": "Could not parse JSON"}
        
        return None

# Test the agent
if __name__ == "__main__":
    print("🤖 Testing Agentic AI Core...\n")
    
    agent = BedrockAgentCore()
    
    # Load data
    inventory = pd.read_csv('../data/inventory.csv')
    competitors = pd.read_csv('../data/competitors.csv')
    inquiries = pd.read_csv('../data/customer_inquiries.csv')
    
    print("🧠 Running agent decision loop...")
    decisions = agent.agent_decision_loop(inventory, competitors, inquiries)
    
    if decisions:
        print("\n✅ Agent decisions generated!")
        print(json.dumps(decisions, indent=2))
    else:
        print("\n❌ No decisions generated")