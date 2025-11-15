import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from faker import Faker
import random
import json

fake = Faker()
np.random.seed(42)

def generate_inventory(n=50):
    """Generate realistic vehicle inventory"""
    
    vehicles_db = {
        'Toyota': {
            'models': ['Camry', 'Corolla', 'RAV4', 'Highlander', 'Tacoma'],
            'price_range': (25000, 45000),
            'popularity': 0.85
        },
        'Honda': {
            'models': ['Accord', 'Civic', 'CR-V', 'Pilot'],
            'price_range': (24000, 42000),
            'popularity': 0.80
        },
        'Ford': {
            'models': ['F-150', 'Escape', 'Explorer', 'Mustang', 'Bronco'],
            'price_range': (28000, 55000),
            'popularity': 0.75
        },
        'Chevrolet': {
            'models': ['Silverado', 'Equinox', 'Traverse', 'Tahoe'],
            'price_range': (27000, 52000),
            'popularity': 0.70
        },
        'Tesla': {
            'models': ['Model 3', 'Model Y', 'Model S'],
            'price_range': (42000, 85000),
            'popularity': 0.90
        },
        'BMW': {
            'models': ['3 Series', '5 Series', 'X3', 'X5'],
            'price_range': (45000, 75000),
            'popularity': 0.65
        },
        'Mercedes-Benz': {
            'models': ['C-Class', 'E-Class', 'GLC', 'GLE'],
            'price_range': (48000, 78000),
            'popularity': 0.60
        }
    }
    
    inventory = []
    
    for i in range(n):
        make = random.choice(list(vehicles_db.keys()))
        vehicle_info = vehicles_db[make]
        model = random.choice(vehicle_info['models'])
        year = random.randint(2021, 2024)
        
        # More realistic mileage based on year
        age = 2024 - year
        base_mileage = age * random.randint(8000, 15000)
        mileage = base_mileage + random.randint(0, 5000)
        
        # Pricing logic
        price_min, price_max = vehicle_info['price_range']
        base_price = random.randint(price_min, price_max)
        
        # Adjust for year and mileage
        depreciation = (2024 - year) * 0.10
        mileage_factor = (mileage / 50000) * 0.05
        
        cost = base_price * (1 - depreciation - mileage_factor)
        current_price = cost * random.uniform(1.15, 1.35)  # 15-35% markup
        
        # Days in inventory (some aged inventory)
        days_weights = [0.4, 0.3, 0.2, 0.1]  # Most are fresh
        days_ranges = [(1, 30), (31, 60), (61, 90), (91, 150)]
        days_range = random.choices(days_ranges, weights=days_weights)[0]
        days_in_inventory = random.randint(*days_range)
        
        inventory.append({
            'vin': fake.bothify(text='???########').upper(),
            'stock_number': f'STK{10000 + i}',
            'make': make,
            'model': model,
            'year': year,
            'mileage': mileage,
            'cost': round(cost, 2),
            'current_price': round(current_price, 2),
            'msrp': round(base_price, 2),
            'days_in_inventory': days_in_inventory,
            'color': random.choice(['Black', 'White', 'Silver', 'Gray', 'Blue', 'Red', 'Green']),
            'condition': 'New' if year == 2024 else random.choice(['Used', 'Certified Pre-Owned']),
            'trim': random.choice(['Base', 'LE', 'XLE', 'Limited', 'Sport', 'Premium']),
            'transmission': random.choice(['Automatic', 'Manual', 'CVT']),
            'fuel_type': random.choice(['Gasoline', 'Hybrid', 'Electric', 'Diesel']),
            'popularity_score': vehicle_info['popularity'],
            'last_price_change': (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
            'view_count': random.randint(5, 200),
            'inquiry_count': random.randint(0, 15)
        })
    
    return pd.DataFrame(inventory)

def generate_competitor_data(inventory_df):
    """Generate competitor listings for market analysis"""
    
    competitor_data = []
    competitor_names = [
        'AutoNation', 'CarMax', 'Lithia Motors', 'Penske Automotive',
        'Sonic Automotive', 'Local Motors', 'City Auto Group'
    ]
    
    for _, vehicle in inventory_df.iterrows():
        # Generate 3-7 competitor listings per vehicle type
        num_competitors = random.randint(3, 7)
        
        for _ in range(num_competitors):
            # Price variance
            price_factor = random.uniform(0.92, 1.08)
            competitor_price = vehicle['current_price'] * price_factor
            
            # Mileage variance
            mileage_diff = random.randint(-8000, 8000)
            competitor_mileage = max(1000, vehicle['mileage'] + mileage_diff)
            
            competitor_data.append({
                'make': vehicle['make'],
                'model': vehicle['model'],
                'year': vehicle['year'],
                'mileage': competitor_mileage,
                'price': round(competitor_price, 2),
                'dealer_name': random.choice(competitor_names),
                'distance_miles': random.randint(2, 45),
                'listing_date': (datetime.now() - timedelta(days=random.randint(1, 60))).isoformat(),
                'condition': vehicle['condition'],
                'trim': random.choice(['Base', 'LE', 'XLE', 'Limited', 'Sport'])
            })
    
    return pd.DataFrame(competitor_data)

def generate_customer_inquiries(inventory_df, n=25):
    """Generate customer lead data"""
    
    inquiries = []
    
    for i in range(n):
        vehicle = inventory_df.sample(1).iloc[0]
        
        # Customer types
        customer_types = ['hot_lead', 'warm_lead', 'cold_lead', 'price_shopper']
        customer_type = random.choices(
            customer_types,
            weights=[0.15, 0.35, 0.30, 0.20]
        )[0]
        
        # Generate inquiry message
        messages = {
            'hot_lead': [
                f"I'm very interested in the {vehicle['year']} {vehicle['make']} {vehicle['model']}. Can I come see it today?",
                f"Is the {vehicle['make']} {vehicle['model']} still available? I'd like to buy this week.",
                f"I've been looking for exactly this car! What's your best price?"
            ],
            'warm_lead': [
                f"Can you tell me more about the {vehicle['year']} {vehicle['make']} {vehicle['model']}?",
                f"I'm interested in this vehicle. Does it have a clean title?",
                f"What financing options do you have for the {vehicle['model']}?"
            ],
            'cold_lead': [
                f"Just browsing. Is this {vehicle['make']} {vehicle['model']} negotiable on price?",
                f"I might be interested. Can you send me more photos?",
                f"How much would you take for this?"
            ],
            'price_shopper': [
                f"I found this same car for ${vehicle['current_price'] * 0.95:.0f} elsewhere. Can you match?",
                f"Your price seems high. What's your absolute lowest price?",
                f"I'm comparing prices. What discounts can you offer?"
            ]
        }
        
        inquiries.append({
            'inquiry_id': f'INQ{20000 + i}',
            'vin': vehicle['vin'],
            'stock_number': vehicle['stock_number'],
            'customer_name': fake.name(),
            'customer_email': fake.email(),
            'customer_phone': fake.phone_number(),
            'customer_type': customer_type,
            'message': random.choice(messages[customer_type]),
            'timestamp': (datetime.now() - timedelta(hours=random.randint(1, 72))).isoformat(),
            'status': random.choice(['new', 'pending', 'responded']),
            'preferred_contact': random.choice(['email', 'phone', 'text']),
            'budget_max': round(vehicle['current_price'] * random.uniform(0.90, 1.05), 2),
            'trade_in': random.choice([True, False]),
            'financing_needed': random.choice([True, False])
        })
    
    return pd.DataFrame(inquiries)

def generate_sales_history(n=150):
    """Generate historical sales for ML training"""
    
    sales = []
    
    for i in range(n):
        sale_date = datetime.now() - timedelta(days=random.randint(1, 365))
        
        make = random.choice(['Toyota', 'Honda', 'Ford', 'Chevrolet', 'Tesla'])
        year = random.randint(2019, 2023)
        
        base_price = random.randint(22000, 60000)
        sold_price = base_price * random.uniform(0.85, 0.98)
        
        sales.append({
            'sale_id': f'SALE{30000 + i}',
            'sale_date': sale_date.isoformat(),
            'make': make,
            'year': year,
            'original_price': round(base_price, 2),
            'sold_price': round(sold_price, 2),
            'discount': round(base_price - sold_price, 2),
            'days_to_sell': random.randint(3, 120),
            'season': (sale_date.month - 1) // 3,  # 0=Q1, 1=Q2, 2=Q3, 3=Q4
            'gross_profit': round(sold_price * random.uniform(0.08, 0.18), 2),
            'financing': random.choice([True, False]),
            'trade_in': random.choice([True, False])
        })
    
    return pd.DataFrame(sales)

# Generate and save all data
if __name__ == "__main__":
    print("🏗️  Generating dealership data...\n")
    
    # Generate datasets
    print("📊 Creating inventory...")
    inventory = generate_inventory(50)
    
    print("🔍 Creating competitor data...")
    competitors = generate_competitor_data(inventory)
    
    print("📧 Creating customer inquiries...")
    inquiries = generate_customer_inquiries(inventory, 25)
    
    print("💰 Creating sales history...")
    sales_history = generate_sales_history(150)
    
    # Save to CSV
    inventory.to_csv('data/inventory.csv', index=False)
    competitors.to_csv('data/competitors.csv', index=False)
    inquiries.to_csv('data/customer_inquiries.csv', index=False)
    sales_history.to_csv('data/sales_history.csv', index=False)
    
    # Save summary stats
    summary = {
        'generated_at': datetime.now().isoformat(),
        'inventory_count': len(inventory),
        'competitor_listings': len(competitors),
        'customer_inquiries': len(inquiries),
        'sales_history': len(sales_history),
        'total_inventory_value': float(inventory['current_price'].sum()),
        'avg_days_in_stock': float(inventory['days_in_inventory'].mean()),
        'aged_inventory_count': len(inventory[inventory['days_in_inventory'] > 60])
    }
    
    with open('data/summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("\n✅ Data generation complete!")
    print(f"   • Inventory: {len(inventory)} vehicles")
    print(f"   • Competitor listings: {len(competitors)}")
    print(f"   • Customer inquiries: {len(inquiries)}")
    print(f"   • Sales history: {len(sales_history)} records")
    print(f"   • Total inventory value: ${inventory['current_price'].sum():,.2f}")
    print(f"   • Aged inventory (60+ days): {len(inventory[inventory['days_in_inventory'] > 60])}")