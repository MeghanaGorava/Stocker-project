from flask import Flask, render_template, request, redirect, url_for, flash, session
import boto3, os, uuid, json
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal

app = Flask(__name__)
app.secret_key = "stocker_secret_2024"

# AWS Resource
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
db = boto3.resource('dynamodb', region_name=AWS_REGION)

# --- Database Helper Functions ---

def get_user_by_id(user_id):
    """Finds user by ID since email is the primary Partition Key"""
    table = db.Table('stocker_users')
    response = table.scan(FilterExpression=Attr('id').eq(user_id))
    return response['Items'][0] if response['Items'] else None

@app.route('/delete_trader/<string:trader_id>', methods=['POST'])
def delete_trader(trader_id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    user = get_user_by_id(trader_id)
    if user:
        # Delete from Users table
        db.Table('stocker_users').delete_item(Key={'email': user['email']})
        
        # Delete all holdings in Portfolio table
        p_table = db.Table('stocker_portfolio')
        holdings = p_table.query(KeyConditionExpression=Key('user_id').eq(trader_id))
        for item in holdings.get('Items', []):
            p_table.delete_item(Key={'user_id': trader_id, 'stock_id': item['stock_id']})
            
        flash("Trader and associated portfolio successfully removed.", "success")
    return redirect(url_for('service01'))

@app.route('/buy_stock/<string:stock_id>', methods=['POST'])
def buy_stock(stock_id):
    if session.get('role') != 'trader': return redirect(url_for('login'))
    
    uid = session['user_id']
    qty = Decimal(request.form.get('quantity', 0))
    price = Decimal("150.00") # Replace with dynamic price from your stock table
    
    p_table = db.Table('stocker_portfolio')
    existing = p_table.get_item(Key={'user_id': uid, 'stock_id': stock_id}).get('Item')
    
    if existing:
        # Calculate new weighted average price
        old_qty = Decimal(str(existing['quantity']))
        old_avg = Decimal(str(existing['average_price']))
        
        total_qty = old_qty + qty
        new_avg = ((old_qty * old_avg) + (qty * price)) / total_qty
        
        p_table.put_item(Item={
            'user_id': uid, 'stock_id': stock_id, 
            'quantity': total_qty, 'average_price': new_avg
        })
    else:
        p_table.put_item(Item={
            'user_id': uid, 'stock_id': stock_id, 
            'quantity': qty, 'average_price': price
        })
    
    flash("Stock purchase completed.", "success")
    return redirect(url_for('dashboard_trader'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
