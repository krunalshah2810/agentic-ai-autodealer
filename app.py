from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
import json
from datetime import datetime, timedelta
import os
from agents.bedrock_agent import BedrockAgentCore
from agents.action_executor import ActionExecutor

app = Flask(__name__)
CORS(app)

# Initialize AI components
agent_core = BedrockAgentCore()
executor = ActionExecutor(dry_run=True)

def load_data():
    """Load all data files"""
    return {
        'inventory': pd.read_csv('data/inventory.csv'),
        'competitors': pd.read_csv('data/competitors.csv'),
        'inquiries': pd.read_csv('data/customer_inquiries.csv'),
        'sales': pd.read_csv('data/sales_history.csv')
    }

@app.route('/')
def dashboard():
    """Main dashboard"""
    
    data = load_data()
    inventory = data['inventory']
    inquiries = data['inquiries']
    
    # Calculate KPIs
    total_inventory = len(inventory)
    total_value = inventory['current_price'].sum()
    avg_days = inventory['days_in_inventory'].mean()
    aged_inventory = len(inventory[inventory['days_in_inventory'] > 60])
    new_inquiries = len(inquiries[inquiries['status'] == 'new'])
    hot_leads = len(inquiries[inquiries['customer_type'] == 'hot_lead'])
    
    # Get recent agent actions
    action_history = executor.get_action_history(limit=20)
    
    return render_template('dashboard.html',
                         total_inventory=total_inventory,
                         total_value=total_value,
                         avg_days=round(avg_days, 1),
                         aged_inventory=aged_inventory,
                         new_inquiries=new_inquiries,
                         hot_leads=hot_leads,
                         action_history=action_history)

@app.route('/api/agent-status')
def agent_status():
    """Get current agent status"""
    
    action_history = executor.get_action_history(limit=1)
    
    if action_history:
        last_run = action_history[-1]
        return jsonify({
            'status': 'active',
            'last_run': last_run.get('timestamp'),
            'total_actions': last_run.get('total_actions', 0),
            'successful_actions': last_run.get('successful_actions', 0)
        })
    
    return jsonify({
        'status': 'idle',
        'last_run': None
    })

@app.route('/api/live-activity')
def live_activity():
    """Get live activity feed"""
    
    action_history = executor.get_action_history(limit=20)
    
    # Flatten all actions into a single feed
    feed = []
    
    for run in reversed(action_history):
        timestamp = run.get('timestamp')
        
        for action_type, actions in run.get('actions_by_type', {}).items():
            for action in actions:
                feed.append({
                    'timestamp': action.get('timestamp', timestamp),
                    'type': action.get('action_type', action_type),
                    'status': action.get('status'),
                    'description': format_action_description(action),
                    'icon': get_action_icon(action.get('action_type', action_type))
                })
    
    return jsonify(feed[:50])  # Return last 50 actions

def format_action_description(action):
    """Format action for display"""
    
    action_type = action.get('action_type', '')
    
    if action_type == 'price_adjustment':
        old = action.get('old_price', 0)
        new = action.get('new_price', 0)
        stock = action.get('stock_number', 'Unknown')
        return f"Adjusted price on {stock}: ${old:,.0f} → ${new:,.0f}"
    
    elif action_type == 'customer_response':
        name = action.get('customer_name', 'Customer')
        subject = action.get('subject', 'inquiry')
        return f"Responded to {name}: {subject}"
    
    elif action_type == 'social_media_post':
        platform = action.get('platform', 'social media')
        return f"Posted to {platform}"
    
    elif action_type == 'urgent_alert':
        return f"Alert: {action.get('message', 'Action required')}"
    
    return "Action completed"

def get_action_icon(action_type):
    """Get emoji icon for action type"""
    
    icons = {
        'price_adjustment': '💰',
        'customer_response': '📧',
        'social_media_post': '📱',
        'urgent_alert': '⚠️'
    }
    
    return icons.get(action_type, '🤖')

@app.route('/api/inventory-analysis')
def inventory_analysis():
    """Inventory analysis charts"""
    
    inventory = pd.read_csv('data/inventory.csv')
    
    # Age distribution
    age_bins = [0, 30, 60, 90, 150]
    age_labels = ['0-30 days', '31-60 days', '61-90 days', '90+ days']
    inventory['age_category'] = pd.cut(
        inventory['days_in_inventory'],
        bins=age_bins,
        labels=age_labels
    )
    
    age_counts = inventory['age_category'].value_counts().sort_index()
    
    fig = go.Figure(data=[
        go.Bar(
            x=age_counts.index,
            y=age_counts.values,
            marker_color=['#10b981', '#f59e0b', '#ef4444', '#991b1b']
        )
    ])
    
    fig.update_layout(
        title='Inventory Age Distribution',
        xaxis_title='Age Category',
        yaxis_title='Number of Vehicles',
        template='plotly_white',
        height=400
    )
    
    return jsonify(json.loads(fig.to_json()))

@app.route('/api/price-position')
def price_position():
    """Price vs market position"""
    
    inventory = pd.read_csv('data/inventory.csv')
    competitors = pd.read_csv('data/competitors.csv')
    
    # Calculate average competitor prices
    comp_avg = competitors.groupby(['make', 'model', 'year'])['price'].mean().reset_index()
    comp_avg.columns = ['make', 'model', 'year', 'comp_avg_price']
    
    # Merge with inventory
    inventory_with_comp = inventory.merge(comp_avg, on=['make', 'model', 'year'], how='left')
    inventory_with_comp['price_diff_pct'] = (
        (inventory_with_comp['current_price'] - inventory_with_comp['comp_avg_price']) / 
        inventory_with_comp['comp_avg_price'] * 100
    )
    
    fig = go.Figure(data=[
        go.Scatter(
            x=inventory_with_comp['days_in_inventory'],
            y=inventory_with_comp['price_diff_pct'],
            mode='markers',
            marker=dict(
                size=10,
                color=inventory_with_comp['days_in_inventory'],
                colorscale='RdYlGn_r',
                showscale=True,
                colorbar=dict(title="Days in Stock")
            ),
            text=[f"{row['year']} {row['make']} {row['model']}" for _, row in inventory_with_comp.iterrows()],
            hovertemplate='%{text}<br>Price vs Market: %{y:.1f}%<br>Days: %{x}<extra></extra>'
        )
    ])
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Market Average")
    
    fig.update_layout(
        title='Pricing Position vs Market',
        xaxis_title='Days in Inventory',
        yaxis_title='Price vs Market Average (%)',
        template='plotly_white',
        height=400
    )
    
    return jsonify(json.loads(fig.to_json()))

@app.route('/api/top-opportunities')
def top_opportunities():
    """Get top opportunities for action"""
    
    inventory = pd.read_csv('data/inventory.csv')
    competitors = pd.read_csv('data/competitors.csv')
    
    # Calculate opportunity score
    comp_avg = competitors.groupby(['make', 'model', 'year'])['price'].mean().reset_index()
    comp_avg.columns = ['make', 'model', 'year', 'comp_avg_price']
    
    inventory_analysis = inventory.merge(comp_avg, on=['make', 'model', 'year'], how='left')
    inventory_analysis['price_vs_market'] = (
        (inventory_analysis['current_price'] - inventory_analysis['comp_avg_price']) / 
        inventory_analysis['comp_avg_price']
    )
    
    # Opportunity score: high if overpriced + aged
    inventory_analysis['opportunity_score'] = (
        inventory_analysis['days_in_inventory'] / 10 + 
        inventory_analysis['price_vs_market'] * 100
    )
    
    top_opps = inventory_analysis.nlargest(10, 'opportunity_score')[[
        'stock_number', 'year', 'make', 'model', 'current_price',
        'comp_avg_price', 'days_in_inventory', 'opportunity_score'
    ]]
    
    return jsonify(top_opps.to_dict('records'))

@app.route('/api/run-agent', methods=['POST'])
def run_agent_now():
    """Manually trigger agent run"""
    
    try:
        data = load_data()
        
        # Get agent decisions
        decisions = agent_core.agent_decision_loop(
            data['inventory'],
            data['competitors'],
            data['inquiries']
        )
        
        if not decisions:
            return jsonify({'error': 'No decisions generated'}), 500
        
        # Execute actions
        results = executor.execute_all_actions(
            decisions,
            data['inventory'],
            data['inquiries']
        )
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-description/<vin>')
def generate_description(vin):
    """Generate AI description for a vehicle"""
    
    inventory = pd.read_csv('data/inventory.csv')
    vehicle = inventory[inventory['vin'] == vin]
    
    if vehicle.empty:
        return jsonify({'error': 'Vehicle not found'}), 404
    
    vehicle_dict = vehicle.iloc[0].to_dict()
    description = agent_core.generate_vehicle_description(vehicle_dict)
    
    return jsonify({
        'vin': vin,
        'description': description,
        'generated_at': datetime.now().isoformat()
    })

@app.route('/api/customer-inquiries')
def customer_inquiries():
    """Get customer inquiries"""
    
    inquiries = pd.read_csv('data/customer_inquiries.csv')
    new_inquiries = inquiries[inquiries['status'] == 'new'].head(10)
    
    return jsonify(new_inquiries.to_dict('records'))

@app.route('/api/full-inventory')
def full_inventory():
    """Return full inventory data"""
    inventory = pd.read_csv('data/inventory.csv')
    return jsonify(inventory.to_dict('records'))

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')