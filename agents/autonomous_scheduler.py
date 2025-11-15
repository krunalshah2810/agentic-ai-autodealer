import schedule
import time
from datetime import datetime
import pandas as pd
from bedrock_agent import BedrockAgentCore
from action_executor import ActionExecutor
import os
from dotenv import load_dotenv

load_dotenv()

class AutonomousAgent:
    """
    Autonomous agent that runs on a schedule
    This is what makes it truly "agentic" - it works independently
    """
    
    def __init__(self, dry_run=True):
        self.agent_core = BedrockAgentCore()
        self.executor = ActionExecutor(dry_run=dry_run)
        self.is_running = False
        self.run_count = 0
        self.last_run = None
        
    def run_agent_cycle(self):
        """Execute one complete agent cycle"""
        
        print("\n" + "="*60)
        print(f"🤖 AUTONOMOUS AGENT CYCLE #{self.run_count + 1}")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        
        try:
            # Load latest data
            print("📊 Loading data...")
            inventory = pd.read_csv('../data/inventory.csv')
            competitors = pd.read_csv('../data/competitors.csv')
            inquiries = pd.read_csv('../data/customer_inquiries.csv')
            
            print(f"   • Inventory: {len(inventory)} vehicles")
            print(f"   • Competitors: {len(competitors)} listings")
            print(f"   • Inquiries: {len(inquiries[inquiries['status'] == 'new'])} new")
            
            # Run agent decision-making
            print("\n🧠 Agent analyzing situation and making decisions...")
            decisions = self.agent_core.agent_decision_loop(
                inventory, 
                competitors, 
                inquiries
            )
            
            if not decisions:
                print("❌ No decisions generated")
                return
            
            # Display analysis summary
            if 'analysis_summary' in decisions:
                print(f"\n📋 Analysis: {decisions['analysis_summary']}")
            
            # Execute actions
            print("\n🎬 Executing autonomous actions...")
            results = self.executor.execute_all_actions(
                decisions, 
                inventory, 
                inquiries
            )
            
            # Summary
            print(f"\n✅ Cycle complete!")
            print(f"   • Total actions: {results['total_actions']}")
            print(f"   • Successful: {results['successful_actions']}")
            print(f"   • Failed: {results['failed_actions']}")
            
            if 'actions_by_type' in results:
                print(f"\n   Actions breakdown:")
                for action_type, actions in results['actions_by_type'].items():
                    print(f"   • {action_type}: {len(actions)}")
            
            self.run_count += 1
            self.last_run = datetime.now()
            
        except Exception as e:
            print(f"\n❌ Error in agent cycle: {e}")
            import traceback
            traceback.print_exc()
    
    def start_autonomous_mode(self, interval_minutes=60):
        """Start the agent in autonomous mode"""
        
        print("\n" + "="*60)
        print("🚀 STARTING AUTONOMOUS AGENT")
        print("="*60)
        print(f"Mode: {'DRY RUN (Simulation)' if self.executor.dry_run else 'LIVE (Real actions)'}")
        print(f"Interval: Every {interval_minutes} minutes")
        print(f"Press Ctrl+C to stop")
        print("="*60 + "\n")
        
        self.is_running = True
        
        # Run immediately
        self.run_agent_cycle()
        
        # Schedule future runs
        schedule.every(interval_minutes).minutes.do(self.run_agent_cycle)
        
        # Keep running
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)
    
    def stop(self):
        """Stop the autonomous agent"""
        self.is_running = False
        print("\n🛑 Autonomous agent stopped")

# Run autonomous agent
if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    dry_run = '--live' not in sys.argv
    interval = int(os.getenv('AGENT_RUN_INTERVAL_MINUTES', 60))
    
    # For demo, run every 5 minutes
    if '--demo' in sys.argv:
        interval = 5
    
    agent = AutonomousAgent(dry_run=dry_run)
    
    try:
        agent.start_autonomous_mode(interval_minutes=interval)
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping agent...")
        agent.stop()
        print("👋 Goodbye!")