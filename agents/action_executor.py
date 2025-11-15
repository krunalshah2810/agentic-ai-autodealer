import json
import os
from datetime import datetime
import pandas as pd
from typing import Dict, List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class ActionExecutor:
    """
    Executes actions decided by the AI agent
    This is what makes it "agentic" - it actually DOES things
    """
    
    def __init__(self, dry_run=False):
        """
        Args:
            dry_run: If True, only simulates actions without executing
        """
        self.dry_run = dry_run
        self.action_log = []
        self.log_file = 'logs/agent_actions.json'
        
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
        
    def execute_all_actions(self, decisions: Dict, inventory_df: pd.DataFrame, inquiries_df: pd.DataFrame):
        """Execute all actions from agent decisions"""
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_actions': 0,
            'successful_actions': 0,
            'failed_actions': 0,
            'actions_by_type': {},
            'details': []
        }
        
        # Execute price adjustments
        if 'price_adjustments' in decisions:
            price_results = self.execute_price_adjustments(
                decisions['price_adjustments'], 
                inventory_df
            )
            results['actions_by_type']['price_adjustments'] = price_results
            results['total_actions'] += len(price_results)
            results['successful_actions'] += sum(1 for r in price_results if r['status'] == 'success')
        
        # Execute customer responses
        if 'customer_responses' in decisions:
            email_results = self.execute_customer_responses(
                decisions['customer_responses'],
                inquiries_df
            )
            results['actions_by_type']['customer_responses'] = email_results
            results['total_actions'] += len(email_results)
            results['successful_actions'] += sum(1 for r in email_results if r['status'] == 'success')
        
        # Execute social media posts
        if 'social_media_posts' in decisions:
            social_results = self.execute_social_media_posts(
                decisions['social_media_posts']
            )
            results['actions_by_type']['social_media_posts'] = social_results
            results['total_actions'] += len(social_results)
            results['successful_actions'] += sum(1 for r in social_results if r['status'] == 'success')
        
        # Log urgent alerts
        if 'urgent_alerts' in decisions:
            alert_results = self.log_urgent_alerts(
                decisions['urgent_alerts']
            )
            results['actions_by_type']['urgent_alerts'] = alert_results
            results['total_actions'] += len(alert_results)
            results['successful_actions'] += len(alert_results)
        
        results['failed_actions'] = results['total_actions'] - results['successful_actions']
        
        # Save to log
        self._save_action_log(results)
        
        return results
    
    def execute_price_adjustments(self, adjustments: List[Dict], inventory_df: pd.DataFrame) -> List[Dict]:
        """Execute price changes in the system"""
        
        results = []
        
        print(f"\n💰 Executing {len(adjustments)} price adjustments...")
        
        for adjustment in adjustments:
            try:
                vin = adjustment.get('vin')
                new_price = adjustment.get('recommended_price')
                reason = adjustment.get('reason', 'AI recommendation')
                
                if not vin or not new_price:
                    print(f"⚠️ Skipping adjustment - missing VIN or price")
                    results.append({
                        'status': 'failed',
                        'error': 'Missing VIN or price',
                        'timestamp': datetime.now().isoformat()
                    })
                    continue
                
                # Find vehicle in inventory
                vehicle = inventory_df[inventory_df['vin'] == vin]
                
                if vehicle.empty:
                    print(f"⚠️ Vehicle not found: {vin}")
                    results.append({
                        'vin': vin,
                        'status': 'failed',
                        'error': 'Vehicle not found',
                        'timestamp': datetime.now().isoformat()
                    })
                    continue
                
                old_price = vehicle.iloc[0]['current_price']
                
                if self.dry_run:
                    action_type = 'SIMULATED'
                else:
                    # Update the CSV
                    inventory_df.loc[inventory_df['vin'] == vin, 'current_price'] = new_price
                    inventory_df.loc[inventory_df['vin'] == vin, 'last_price_change'] = datetime.now().isoformat()
                    inventory_df.to_csv('data/inventory.csv', index=False)
                    action_type = 'EXECUTED'
                
                result = {
                    'action_type': 'price_adjustment',
                    'status': 'success',
                    'vin': vin,
                    'stock_number': adjustment.get('stock_number'),
                    'old_price': float(old_price),
                    'new_price': float(new_price),
                    'adjustment_amount': float(new_price - old_price),
                    'adjustment_percent': float((new_price - old_price) / old_price * 100),
                    'reason': reason,
                    'confidence': adjustment.get('confidence', 0.8),
                    'urgency': adjustment.get('urgency', 'medium'),
                    'execution_type': action_type,
                    'timestamp': datetime.now().isoformat()
                }
                
                results.append(result)
                
                print(f"  {'💰' if not self.dry_run else '💭'} {adjustment.get('stock_number')}: ${old_price:,.0f} → ${new_price:,.0f} ({action_type})")
                
            except Exception as e:
                print(f"  ❌ Error: {str(e)}")
                results.append({
                    'vin': adjustment.get('vin'),
                    'status': 'failed',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        print(f"✅ Completed: {sum(1 for r in results if r['status'] == 'success')}/{len(results)} successful\n")
        
        return results
    
    def execute_customer_responses(self, responses: List[Dict], inquiries_df: pd.DataFrame) -> List[Dict]:
        """Send email responses to customers"""
        
        results = []
        
        for response in responses:
            try:
                inquiry_id = response.get('inquiry_id')
                
                # Find inquiry
                inquiry = inquiries_df[inquiries_df['inquiry_id'] == inquiry_id]
                
                if inquiry.empty:
                    results.append({
                        'inquiry_id': inquiry_id,
                        'status': 'failed',
                        'error': 'Inquiry not found',
                        'timestamp': datetime.now().isoformat()
                    })
                    continue
                
                customer_email = inquiry.iloc[0]['customer_email']
                customer_name = inquiry.iloc[0]['customer_name']
                
                if self.dry_run:
                    action_type = 'SIMULATED'
                    # Just log the email
                    email_log = {
                        'to': customer_email,
                        'subject': response.get('response_subject'),
                        'body_preview': response.get('response_body')[:200] + '...'
                    }
                else:
                    # In production, this would send actual email via SendGrid/AWS SES
                    action_type = 'EXECUTED'
                    email_log = self._send_email(
                        to=customer_email,
                        subject=response.get('response_subject'),
                        body=response.get('response_body')
                    )
                    
                    # Update inquiry status
                    inquiries_df.loc[inquiries_df['inquiry_id'] == inquiry_id, 'status'] = 'responded'
                    inquiries_df.to_csv('data/customer_inquiries.csv', index=False)
                
                result = {
                    'action_type': 'customer_response',
                    'status': 'success',
                    'inquiry_id': inquiry_id,
                    'customer_name': customer_name,
                    'customer_email': customer_email,
                    'subject': response.get('response_subject'),
                    'offer_price': response.get('offer_price'),
                    'strategy': response.get('strategy'),
                    'execution_type': action_type,
                    'email_log': email_log,
                    'timestamp': datetime.now().isoformat()
                }
                
                results.append(result)
                
                print(f"{'📧' if not self.dry_run else '💭'} Email {'sent' if not self.dry_run else 'simulation'}: {customer_name} - {response.get('response_subject')}")
                
            except Exception as e:
                results.append({
                    'inquiry_id': response.get('inquiry_id'),
                    'status': 'failed',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        return results
    
    def execute_social_media_posts(self, posts: List[Dict]) -> List[Dict]:
        """Create social media posts"""
        
        results = []
        
        for post in posts:
            try:
                platform = post.get('platform')
                content = post.get('content')
                vehicle_vin = post.get('vehicle_vin')
                
                if self.dry_run:
                    action_type = 'SIMULATED'
                else:
                    # In production, this would post to actual social media APIs
                    action_type = 'EXECUTED'
                    # For demo, save to file
                    self._save_social_post(platform, content, vehicle_vin)
                
                result = {
                    'action_type': 'social_media_post',
                    'status': 'success',
                    'platform': platform,
                    'content_preview': content[:100] + '...' if len(content) > 100 else content,
                    'vehicle_vin': vehicle_vin,
                    'hashtags': post.get('hashtags', []),
                    'execution_type': action_type,
                    'timestamp': datetime.now().isoformat()
                }
                
                results.append(result)
                
                print(f"{'📱' if not self.dry_run else '💭'} Social post {'created' if not self.dry_run else 'simulation'}: {platform} - {content[:50]}...")
                
            except Exception as e:
                results.append({
                    'platform': post.get('platform'),
                    'status': 'failed',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        return results
    
    def log_urgent_alerts(self, alerts: List[Dict]) -> List[Dict]:
        """Log urgent items that need human attention"""
        
        results = []
        
        for alert in alerts:
            result = {
                'action_type': 'urgent_alert',
                'status': 'logged',
                'priority': alert.get('priority'),
                'category': alert.get('category'),
                'message': alert.get('message'),
                'recommended_action': alert.get('recommended_action'),
                'timestamp': datetime.now().isoformat()
            }
            
            results.append(result)
            
            priority_emoji = '🚨' if alert.get('priority') == 'high' else '⚠️' if alert.get('priority') == 'medium' else 'ℹ️'
            print(f"{priority_emoji} Alert [{alert.get('priority')}]: {alert.get('message')}")
        
        return results
    
    def _send_email(self, to: str, subject: str, body: str) -> Dict:
        """Send actual email (placeholder for demo)"""
        
        # In production, use SendGrid, AWS SES, or SMTP
        # For demo, we just log it
        
        email_log = {
            'sent': True,
            'to': to,
            'subject': subject,
            'timestamp': datetime.now().isoformat(),
            'method': 'demo_mode'
        }
        
        # Save to file for demo purposes
        os.makedirs('logs/emails', exist_ok=True)
        filename = f"logs/emails/email_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(filename, 'w') as f:
            f.write(f"To: {to}\n")
            f.write(f"Subject: {subject}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"\n{body}\n")
        
        return email_log
    
    def _save_social_post(self, platform: str, content: str, vehicle_vin: str):
        """Save social media post for demo"""
        
        os.makedirs('logs/social', exist_ok=True)
        filename = f"logs/social/{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(filename, 'w') as f:
            f.write(f"Platform: {platform}\n")
            f.write(f"Vehicle VIN: {vehicle_vin}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"\n{content}\n")
    
    def _save_action_log(self, results: Dict):
        """Save action log to file"""
        
        # Load existing logs
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = []
        
        # Append new results
        logs.append(results)
        
        # Keep only last 100 logs
        logs = logs[-100:]
        
        # Save
        with open(self.log_file, 'w') as f:
            json.dump(logs, f, indent=2)
    
    def get_action_history(self, limit=50):
        """Retrieve action history"""
        
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                logs = json.load(f)
                return logs[-limit:]
        
        return []

# Test the executor
if __name__ == "__main__":
    print("🎬 Testing Action Executor...\n")
    
    from bedrock_agent import BedrockAgentCore
    import pandas as pd
    
    # Load data
    inventory = pd.read_csv('data/inventory.csv')
    competitors = pd.read_csv('data/competitors.csv')
    inquiries = pd.read_csv('data/customer_inquiries.csv')
    
    # Run agent to get decisions
    agent = BedrockAgentCore()
    print("🧠 Getting agent decisions...")
    decisions = agent.agent_decision_loop(inventory, competitors, inquiries)
    
    if decisions:
        print("\n✅ Decisions received!")
        
        # Execute actions (dry run)
        executor = ActionExecutor(dry_run=True)
        print("\n🎬 Executing actions (DRY RUN)...\n")
        results = executor.execute_all_actions(decisions, inventory, inquiries)
        
        print(f"\n📊 Execution Summary:")
        print(f"   Total actions: {results['total_actions']}")
        print(f"   Successful: {results['successful_actions']}")
        print(f"   Failed: {results['failed_actions']}")
        
        print(f"\n📋 Actions by type:")
        for action_type, actions in results['actions_by_type'].items():
            print(f"   {action_type}: {len(actions)}")
    else:
        print("\n❌ No decisions to execute")