import boto3
import uuid
import os
from decimal import Decimal
from datetime import datetime, date

# --- AWS Configuration ---
# Automatically detects if running locally (env vars) or on EC2 (IAM Role)
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

# Initialize DynamoDB Resource and Client
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
client = boto3.client('dynamodb', region_name=AWS_REGION)

# Table Names
USER_TABLE = 'stocker_users'
STOCK_TABLE = 'stocker_stocks'
TRANSACTION_TABLE = 'stocker_transactions'
PORTFOLIO_TABLE = 'stocker_portfolio'

def create_tables():
    """Creates the necessary tables for the Stocker application."""
    existing_tables = client.list_tables()['TableNames']
    
    # Table Configurations
    configs = [
        {
            'TableName': USER_TABLE,
            'KeySchema': [{'AttributeName': 'email', 'KeyType': 'HASH'}],
            'AttributeDefinitions': [{'AttributeName': 'email', 'AttributeType': 'S'}]
        },
        {
            'TableName': STOCK_TABLE,
            'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
            'AttributeDefinitions': [{'AttributeName': 'id', 'AttributeType': 'S'}]
        },
        {
            'TableName': TRANSACTION_TABLE,
            'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
            'AttributeDefinitions': [{'AttributeName': 'id', 'AttributeType': 'S'}]
        },
        {
            'TableName': PORTFOLIO_TABLE,
            'KeySchema': [
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'stock_id', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'stock_id', 'AttributeType': 'S'}
            ]
        }
    ]

    for config in configs:
        if config['TableName'] not in existing_tables:
            print(f"Creating {config['TableName']}...")
            table = dynamodb.create_table(
                TableName=config['TableName'],
                KeySchema=config['KeySchema'],
                AttributeDefinitions=config['AttributeDefinitions'],
                BillingMode='PAY_PER_REQUEST'
            )
            table.meta.client.get_waiter('table_exists').wait(TableName=config['TableName'])
        else:
            print(f"Table {config['TableName']} already exists.")

def seed_data():
    """Seeds users, stocks, and sample transactions."""
    # 1. Seed Users
    user_table = dynamodb.Table(USER_TABLE)
    users = [
        {"id": str(uuid.uuid4()), "username": "AdminUser", "email": "admin@stocker.com", "password": "password123", "role": "admin"},
        {"id": str(uuid.uuid4()), "username": "TraderOne", "email": "trader@stocker.com", "password": "password123", "role": "trader"}
    ]
    
    trader1_ref = None
    for u in users:
        if 'Item' not in user_table.get_item(Key={'email': u['email']}):
            user_table.put_item(Item=u)
            print(f"Added User: {u['email']}")
        if u['role'] == 'trader': trader1_ref = u

    # 2. Seed Nifty 50 Stocks
    stock_table = dynamodb.Table(STOCK_TABLE)
    stocks_to_add = [
        {"id": str(uuid.uuid4()), "symbol": "RELIANCE", "name": "Reliance Industries Ltd", "price": Decimal('2500.00'), "sector": "Energy", "date_added": date.today().isoformat()},
        {"id": str(uuid.uuid4()), "symbol": "TCS", "name": "Tata Consultancy Services Ltd", "price": Decimal('3600.00'), "sector": "IT", "date_added": date.today().isoformat()},
        {"id": str(uuid.uuid4()), "symbol": "INFY", "name": "Infosys Ltd", "price": Decimal('1500.00'), "sector": "IT", "date_added": date.today().isoformat()},
        {"id": str(uuid.uuid4()), "symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "price": Decimal('1600.00'), "sector": "Financials", "date_added": date.today().isoformat()}
    ]
    
    stock_ids = {}
    for s in stocks_to_add:
        # Check by symbol to avoid duplicates
        res = stock_table.scan(FilterExpression=boto3.dynamodb.conditions.Attr('symbol').eq(s['symbol']))
        if not res.get('Items'):
            stock_table.put_item(Item=s)
            stock_ids[s['symbol']] = s['id']
            print(f"Added Stock: {s['symbol']}")
        else:
            stock_ids[s['symbol']] = res['Items'][0]['id']

    # 3. Seed Sample Portfolio (TraderOne owns RELIANCE)
    if trader1_ref and 'RELIANCE' in stock_ids:
        portfolio_table = dynamodb.Table(PORTFOLIO_TABLE)
        portfolio_table.put_item(Item={
            'user_id': trader1_ref['id'],
            'stock_id': stock_ids['RELIANCE'],
            'quantity': Decimal('10'),
            'average_price': Decimal('2500.00')
        })
        print(f"Seeded sample portfolio for {trader1_ref['email']}")

if __name__ == "__main__":
    print("--- Starting DynamoDB Initialization ---")
    create_tables()
    seed_data()
    print("--- Setup Complete ---")
