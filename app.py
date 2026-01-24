from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, timedelta
import secrets
import sqlite3
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
import pickle
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))


DATABASE = 'shisanyama.db'

# SIDE PRICES CONFIGURATION
SIDE_PRICES = {
    'Uphuthu': 20,
    'Jeqe': 30
}

# ============================================
# DATABASE INITIALIZATION
# ============================================

def init_db():
    """Initialize database with all required tables"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Users table - UPDATED with puncher role
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Menu items table - UPDATED with requires_side field
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT NOT NULL,
            stock INTEGER NOT NULL,
            requires_side INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            total REAL NOT NULL,
            status TEXT NOT NULL,
            payment_method TEXT NOT NULL DEFAULT 'cash',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ready_time TIMESTAMP,
            completed_at TIMESTAMP,
            cashier_id INTEGER,
            FOREIGN KEY (cashier_id) REFERENCES users(id)
        )
    ''')
    
    # Order items table - UPDATED with side_option field
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            menu_item_id INTEGER NOT NULL,
            menu_item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            side_option TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
        )
    ''')
    
    # Stock history table - NEW for puncher tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            menu_item_id INTEGER NOT NULL,
            menu_item_name TEXT NOT NULL,
            quantity_change INTEGER NOT NULL,
            stock_before INTEGER NOT NULL,
            stock_after INTEGER NOT NULL,
            change_type TEXT NOT NULL,
            notes TEXT,
            puncher_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (menu_item_id) REFERENCES menu_items(id),
            FOREIGN KEY (puncher_id) REFERENCES users(id)
        )
    ''')
    
    # Insert default users if not exists
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] == 0:
        default_users = [
            ('cashier', 'cash123', 'cashier'),
            ('kitchen', 'cook123', 'kitchen'),
            ('admin', 'admin123', 'admin'),
            ('puncher', 'stock123', 'puncher')
        ]
        cursor.executemany('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', default_users)
    
    # Check if puncher exists, if not add it
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = ?', ('puncher',))
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', 
                      ('puncher', 'stock123', 'puncher'))
    
    # Check if menu items exist, if not insert default ones
    cursor.execute('SELECT COUNT(*) FROM menu_items')
    if cursor.fetchone()[0] == 0:
        # New menu items with your meats (requires_side=1 for meats)
        # Meat base prices (sides will add R20 for Uphuthu, R30 for Jeqe)
        default_menu = [
            # Meats (requires_side = 1) - Base prices without sides
            ('Boiled Beef', 120, 'Meat', 50, 1),
            ('Usu', 100, 'Meat', 40, 1),
            ('Fried Liver (Isibindi)', 95, 'Meat', 45, 1),
            ('Fried Thumbu', 90, 'Meat', 35, 1),
            ('Braaied Beef', 130, 'Meat', 40, 1),
            ('Braaied Pork', 125, 'Meat', 35, 1),
            ('Braaied Wors', 80, 'Meat', 50, 1),
            ('Inqina', 95, 'Meat', 30, 1),
            ('Fried Inhliziyo', 105, 'Meat', 30, 1),
            # Sides (requires_side = 0) - Can be ordered separately
            ('Uphuthu', 20, 'Sides', 100, 0),
            ('Jeqe', 30, 'Sides', 100, 0),
            ('Chakalaka', 20, 'Sides', 80, 0),
            ('Salad', 30, 'Sides', 50, 0),
            # Drinks (requires_side = 0)
            ('Soft Drink', 15, 'Drinks', 120, 0),
            ('Beer', 25, 'Drinks', 90, 0)
        ]
        cursor.executemany('INSERT INTO menu_items (name, price, category, stock, requires_side) VALUES (?, ?, ?, ?, ?)', default_menu)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

# Initialize database on startup
init_db()

# ============================================
# DATABASE HELPER FUNCTIONS
# ============================================

def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def get_user_id(username):
    """Get user ID by username"""
    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user['id'] if user else None

def get_menu_items():
    """Get all menu items"""
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM menu_items ORDER BY category, name').fetchall()
    conn.close()
    return [dict(item) for item in items]

def create_order_db(customer_name, items, total, cashier_username, payment_method='cash'):
    """Create new order in database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cashier_id = get_user_id(cashier_username)
    
    # Insert order
    cursor.execute('''
        INSERT INTO orders (customer_name, total, status, payment_method, timestamp, ready_time, cashier_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        customer_name,
        total,
        'pending',
        payment_method,
        datetime.now(),
        datetime.now() + timedelta(minutes=15),
        cashier_id
    ))
    
    order_id = cursor.lastrowid
    
    # Insert order items with side option and adjusted price
    for item in items:
        side_option = item.get('side_option', None)
        # The price is already calculated in frontend with sides included
        final_price = item['price']
        
        cursor.execute('''
            INSERT INTO order_items (order_id, menu_item_id, menu_item_name, quantity, price, side_option)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (order_id, item['id'], item['name'], item['quantity'], final_price, side_option))
        
        # Get current stock
        current = cursor.execute('SELECT stock FROM menu_items WHERE id = ?', (item['id'],)).fetchone()
        stock_before = current['stock']
        stock_after = stock_before - item['quantity']
        
        # Update stock
        cursor.execute('''
            UPDATE menu_items 
            SET stock = stock - ?
            WHERE id = ?
        ''', (item['quantity'], item['id']))
        
        # Log stock change in history
        cursor.execute('''
            INSERT INTO stock_history (menu_item_id, menu_item_name, quantity_change, stock_before, stock_after, change_type, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (item['id'], item['name'], -item['quantity'], stock_before, stock_after, 'sale', f'Order #{order_id}'))
    
    conn.commit()
    
    # Get the created order
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    conn.close()
    
    return dict(order)

def get_all_orders_db():
    """Get all orders with items"""
    conn = get_db_connection()
    orders = conn.execute('SELECT * FROM orders ORDER BY timestamp DESC').fetchall()
    
    orders_list = []
    for order in orders:
        order_dict = dict(order)
        items = conn.execute('''
            SELECT menu_item_name as name, quantity, price, side_option
            FROM order_items 
            WHERE order_id = ?
        ''', (order['id'],)).fetchall()
        order_dict['items'] = [dict(item) for item in items]
        orders_list.append(order_dict)
    
    conn.close()
    return orders_list

def complete_order_db(order_id):
    """Mark order as completed"""
    conn = get_db_connection()
    conn.execute('''
        UPDATE orders 
        SET status = ?, completed_at = ?
        WHERE id = ?
    ''', ('ready', datetime.now(), order_id))
    conn.commit()
    
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    conn.close()
    return dict(order) if order else None

def get_daily_stats():
    """Get statistics for today"""
    conn = get_db_connection()
    today = datetime.now().date()
    
    stats = conn.execute('''
        SELECT 
            COUNT(*) as total_orders,
            COALESCE(SUM(total), 0) as total_revenue,
            COALESCE(AVG(total), 0) as avg_order_value,
            COUNT(CASE WHEN status = 'ready' THEN 1 END) as completed_orders,
            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_orders
        FROM orders
        WHERE DATE(timestamp) = ?
    ''', (today,)).fetchone()
    
    conn.close()
    return dict(stats) if stats else {}

def get_monthly_stats():
    """Get statistics for current month"""
    conn = get_db_connection()
    year = datetime.now().year
    month = datetime.now().month
    
    stats = conn.execute('''
        SELECT 
            COUNT(*) as total_orders,
            COALESCE(SUM(total), 0) as total_revenue,
            COALESCE(AVG(total), 0) as avg_order_value
        FROM orders
        WHERE strftime('%Y', timestamp) = ? 
        AND strftime('%m', timestamp) = ?
    ''', (str(year), f'{month:02d}')).fetchone()
    
    conn.close()
    return dict(stats) if stats else {}

def get_popular_items(limit=5):
    """Get most popular items"""
    conn = get_db_connection()
    
    popular = conn.execute('''
        SELECT 
            menu_item_name as name,
            SUM(quantity) as total_quantity
        FROM order_items
        GROUP BY menu_item_name
        ORDER BY total_quantity DESC
        LIMIT ?
    ''', (limit,)).fetchall()
    
    conn.close()
    return [(item['name'], item['total_quantity']) for item in popular]

def get_sales_by_category():
    """Get sales breakdown by category"""
    conn = get_db_connection()
    
    category_sales = conn.execute('''
        SELECT 
            mi.category,
            SUM(oi.quantity * oi.price) as total_sales,
            SUM(oi.quantity) as total_items
        FROM order_items oi
        JOIN menu_items mi ON oi.menu_item_id = mi.id
        GROUP BY mi.category
        ORDER BY total_sales DESC
    ''').fetchall()
    
    conn.close()
    return [dict(cat) for cat in category_sales]

# ============================================
# PUNCHER SPECIFIC FUNCTIONS
# ============================================

def add_menu_item(name, price, category, stock, requires_side, puncher_username):
    """Add new menu item"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    puncher_id = get_user_id(puncher_username)
    
    cursor.execute('''
        INSERT INTO menu_items (name, price, category, stock, requires_side)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, price, category, stock, requires_side))
    
    item_id = cursor.lastrowid
    
    # Log stock addition
    cursor.execute('''
        INSERT INTO stock_history (menu_item_id, menu_item_name, quantity_change, stock_before, stock_after, change_type, puncher_id, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (item_id, name, stock, 0, stock, 'initial', puncher_id, 'Initial stock'))
    
    conn.commit()
    
    item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
    conn.close()
    
    return dict(item) if item else None

def update_menu_item(item_id, name, price, category, requires_side, puncher_username):
    """Update menu item details (not stock)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE menu_items 
        SET name = ?, price = ?, category = ?, requires_side = ?
        WHERE id = ?
    ''', (name, price, category, requires_side, item_id))
    
    conn.commit()
    
    item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
    conn.close()
    
    return dict(item) if item else None

def update_stock(item_id, quantity_change, puncher_username, notes=''):
    """Update stock quantity"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    puncher_id = get_user_id(puncher_username)
    
    # Get current stock
    item = cursor.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
    if not item:
        conn.close()
        return None
    
    stock_before = item['stock']
    stock_after = stock_before + quantity_change
    
    if stock_after < 0:
        conn.close()
        return None
    
    # Update stock
    cursor.execute('''
        UPDATE menu_items 
        SET stock = ?
        WHERE id = ?
    ''', (stock_after, item_id))
    
    # Determine change type
    change_type = 'restock' if quantity_change > 0 else 'adjustment'
    
    # Log stock change
    cursor.execute('''
        INSERT INTO stock_history (menu_item_id, menu_item_name, quantity_change, stock_before, stock_after, change_type, puncher_id, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (item_id, item['name'], quantity_change, stock_before, stock_after, change_type, puncher_id, notes))
    
    conn.commit()
    
    updated_item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
    conn.close()
    
    return dict(updated_item) if updated_item else None

def delete_menu_item(item_id):
    """Delete menu item"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if item has been used in orders
    orders_count = cursor.execute('''
        SELECT COUNT(*) as count FROM order_items WHERE menu_item_id = ?
    ''', (item_id,)).fetchone()
    
    if orders_count['count'] > 0:
        conn.close()
        return {'success': False, 'message': 'Cannot delete item that has been used in orders'}
    
    cursor.execute('DELETE FROM menu_items WHERE id = ?', (item_id,))
    cursor.execute('DELETE FROM stock_history WHERE menu_item_id = ?', (item_id,))
    
    conn.commit()
    conn.close()
    
    return {'success': True, 'message': 'Item deleted successfully'}

def get_stock_history(item_id=None, limit=50):
    """Get stock history"""
    conn = get_db_connection()
    
    if item_id:
        history = conn.execute('''
            SELECT sh.*, u.username as puncher_name
            FROM stock_history sh
            LEFT JOIN users u ON sh.puncher_id = u.id
            WHERE sh.menu_item_id = ?
            ORDER BY sh.timestamp DESC
            LIMIT ?
        ''', (item_id, limit)).fetchall()
    else:
        history = conn.execute('''
            SELECT sh.*, u.username as puncher_name
            FROM stock_history sh
            LEFT JOIN users u ON sh.puncher_id = u.id
            ORDER BY sh.timestamp DESC
            LIMIT ?
        ''', (limit,)).fetchall()
    
    conn.close()
    return [dict(h) for h in history]

# ============================================
# API ROUTE FOR SIDE PRICES
# ============================================

@app.route('/api/side-prices', methods=['GET'])
def get_side_prices():
    """Return side prices for frontend calculation"""
    return jsonify(SIDE_PRICES)

# ============================================
# MACHINE LEARNING FUNCTIONS
# ============================================

class SalesPredictor:
    """Machine Learning model for sales prediction"""
    
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.label_encoders = {}
        self.is_trained = False
        
        if os.path.exists('demand_predictor.pkl'):
            try:
                with open('demand_predictor.pkl', 'rb') as f:
                    loaded = pickle.load(f)
                    self.model = loaded.model
                    self.label_encoders = loaded.label_encoders
                    self.is_trained = True
                    print("Loaded existing ML model")
            except Exception as e:
                print(f"Could not load existing model: {e}")
    
    def prepare_data(self):
        conn = sqlite3.connect(DATABASE)
        query = '''
            SELECT 
                o.id,
                o.timestamp,
                o.total,
                oi.menu_item_id,
                oi.quantity,
                oi.menu_item_name as name,
                mi.category,
                CAST(strftime('%w', o.timestamp) AS INTEGER) as day_of_week,
                CAST(strftime('%H', o.timestamp) AS INTEGER) as hour_of_day,
                CAST(strftime('%m', o.timestamp) AS INTEGER) as month
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN menu_items mi ON oi.menu_item_id = mi.id
            WHERE o.status = 'ready'
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def train_demand_predictor(self):
        try:
            df = self.prepare_data()
            if len(df) < 10:
                print("Not enough data to train model")
                return False
            
            le = LabelEncoder()
            df['category_encoded'] = le.fit_transform(df['category'])
            self.label_encoders['category'] = le
            
            X = df[['day_of_week', 'hour_of_day', 'month', 'category_encoded']]
            y = df['quantity']
            
            self.model.fit(X, y)
            self.is_trained = True
            
            try:
                with open('demand_predictor.pkl', 'wb') as f:
                    pickle.dump(self, f)
                print("Model trained and saved!")
            except Exception as e:
                print(f"Model trained but could not save: {e}")
            
            return True
        except Exception as e:
            print(f"Error training model: {e}")
            return False
    
    def predict_demand(self, category, day_of_week=None, hour_of_day=None, month=None):
        if not self.is_trained:
            return 0
        
        if day_of_week is None:
            day_of_week = datetime.now().weekday()
        if hour_of_day is None:
            hour_of_day = datetime.now().hour
        if month is None:
            month = datetime.now().month
        
        try:
            category_encoded = self.label_encoders['category'].transform([category])[0]
            prediction = self.model.predict([[day_of_week, hour_of_day, month, category_encoded]])
            return max(0, int(prediction[0]))
        except Exception as e:
            print(f"Prediction error: {e}")
            return 0
    
    def get_recommendations(self):
        if not self.is_trained:
            return {
                'message': 'Model not trained yet. Need more order data.',
                'recommendations': {}
            }
        
        recommendations = {}
        categories = ['Meat', 'Sides', 'Drinks']
        
        for category in categories:
            predicted_demand = self.predict_demand(category)
            recommendations[category] = {
                'predicted_demand': predicted_demand,
                'recommendation': f'Stock at least {predicted_demand * 2} items for peak hours'
            }
        
        return {
            'message': 'AI recommendations based on historical data',
            'recommendations': recommendations
        }

predictor = SalesPredictor()

def analyze_peak_hours():
    try:
        conn = sqlite3.connect(DATABASE)
        query = '''
            SELECT 
                CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                COUNT(*) as order_count,
                SUM(total) as revenue
            FROM orders
            WHERE status = 'ready'
            GROUP BY hour
            ORDER BY order_count DESC
            LIMIT 5
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df.to_dict('records') if len(df) > 0 else []
    except Exception as e:
        print(f"Error analyzing peak hours: {e}")
        return []

def analyze_sales_trends(days=30):
    try:
        conn = sqlite3.connect(DATABASE)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        query = '''
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as order_count,
                SUM(total) as revenue,
                AVG(total) as avg_order_value
            FROM orders
            WHERE timestamp BETWEEN ? AND ?
            GROUP BY DATE(timestamp)
            ORDER BY date
        '''
        
        df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        conn.close()
        
        if len(df) > 0:
            revenue_trend = df['revenue'].pct_change().mean() * 100 if len(df) > 1 else 0
            order_trend = df['order_count'].pct_change().mean() * 100 if len(df) > 1 else 0
            
            return {
                'revenue_trend': round(revenue_trend, 2),
                'order_trend': round(order_trend, 2),
                'avg_daily_revenue': round(df['revenue'].mean(), 2),
                'avg_daily_orders': round(df['order_count'].mean(), 2),
                'data': df.to_dict('records')
            }
        return None
    except Exception as e:
        print(f"Error analyzing trends: {e}")
        return None

# ============================================
# FLASK ROUTES
# ============================================

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', 
                       (username, password)).fetchone()
    conn.close()
    
    if user:
        session['username'] = user['username']
        session['role'] = user['role']
        return jsonify({'success': True, 'role': user['role']})
    
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('index'))
    
    role = session.get('role')
    if role == 'cashier':
        menu_items = get_menu_items()
        return render_template('cashier.html', menu_items=menu_items)
    elif role == 'kitchen':
        return render_template('kitchen.html')
    elif role == 'admin':
        return render_template('admin.html')
    elif role == 'puncher':
        return render_template('puncher.html')
    
    return redirect(url_for('index'))

@app.route('/reports/daily')
def daily_report():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))
    return render_template('daily.html')

@app.route('/reports/monthly')
def monthly_report():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))
    return render_template('monthly.html')

# ============================================
# API ROUTES
# ============================================

@app.route('/api/menu', methods=['GET'])
def get_menu():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify(get_menu_items())

@app.route('/api/orders', methods=['GET'])
def get_orders():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify(get_all_orders_db())

@app.route('/api/orders', methods=['POST'])
def create_order():
    if 'username' not in session or session.get('role') != 'cashier':
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    customer_name = data.get('customerName')
    items = data.get('items')
    total = data.get('total')
    payment_method = data.get('paymentMethod', 'cash')
    
    if not customer_name or not items:
        return jsonify({'error': 'Missing required fields'}), 400
    
    order = create_order_db(customer_name, items, total, session['username'], payment_method)
    return jsonify({'success': True, 'order': order})

@app.route('/api/orders/<int:order_id>/complete', methods=['PUT'])
def complete_order(order_id):
    if 'username' not in session or session.get('role') != 'kitchen':
        return jsonify({'error': 'Unauthorized'}), 401
    
    order = complete_order_db(order_id)
    
    if order:
        return jsonify({'success': True, 'order': order})
    
    return jsonify({'error': 'Order not found'}), 404

@app.route('/api/stats', methods=['GET'])
def get_stats():
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    all_orders = get_all_orders_db()
    total_revenue = sum(order['total'] for order in all_orders)
    completed_orders = len([o for o in all_orders if o['status'] == 'ready'])
    pending_orders = len([o for o in all_orders if o['status'] == 'pending'])
    popular_items = get_popular_items(5)
    
    return jsonify({
        'totalRevenue': total_revenue,
        'totalOrders': len(all_orders),
        'completedOrders': completed_orders,
        'pendingOrders': pending_orders,
        'popularItems': popular_items,
        'recentOrders': all_orders[:10]
    })

# ============================================
# PUNCHER API ROUTES
# ============================================

@app.route('/api/puncher/menu', methods=['GET'])
def puncher_get_menu():
    if 'username' not in session or session.get('role') != 'puncher':
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify(get_menu_items())

@app.route('/api/puncher/menu', methods=['POST'])
def puncher_add_item():
    if 'username' not in session or session.get('role') != 'puncher':
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    name = data.get('name')
    price = data.get('price')
    category = data.get('category')
    stock = data.get('stock', 0)
    requires_side = data.get('requiresSide', 0)
    
    if not name or price is None or not category:
        return jsonify({'error': 'Missing required fields'}), 400
    
    item = add_menu_item(name, price, category, stock, requires_side, session['username'])
    
    if item:
        return jsonify({'success': True, 'item': item})
    
    return jsonify({'error': 'Failed to add item'}), 500

@app.route('/api/puncher/menu/<int:item_id>', methods=['PUT'])
def puncher_update_item(item_id):
    if 'username' not in session or session.get('role') != 'puncher':
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    name = data.get('name')
    price = data.get('price')
    category = data.get('category')
    requires_side = data.get('requiresSide', 0)
    
    if not name or price is None or not category:
        return jsonify({'error': 'Missing required fields'}), 400
    
    item = update_menu_item(item_id, name, price, category, requires_side, session['username'])
    
    if item:
        return jsonify({'success': True, 'item': item})
    
    return jsonify({'error': 'Failed to update item'}), 500

@app.route('/api/puncher/menu/<int:item_id>', methods=['DELETE'])
def puncher_delete_item(item_id):
    if 'username' not in session or session.get('role') != 'puncher':
        return jsonify({'error': 'Unauthorized'}), 401
    
    result = delete_menu_item(item_id)
    
    if result['success']:
        return jsonify(result)
    
    return jsonify(result), 400

@app.route('/api/puncher/stock/<int:item_id>', methods=['PUT'])
def puncher_update_stock(item_id):
    if 'username' not in session or session.get('role') != 'puncher':
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    quantity_change = data.get('quantityChange')
    notes = data.get('notes', '')
    
    if quantity_change is None:
        return jsonify({'error': 'Missing quantity change'}), 400
    
    item = update_stock(item_id, quantity_change, session['username'], notes)
    
    if item:
        return jsonify({'success': True, 'item': item})
    
    return jsonify({'error': 'Failed to update stock. Stock cannot be negative.'}), 400

@app.route('/api/puncher/stock-history', methods=['GET'])
def puncher_get_stock_history():
    if 'username' not in session or session.get('role') != 'puncher':
        return jsonify({'error': 'Unauthorized'}), 401
    
    item_id = request.args.get('item_id', None, type=int)
    limit = request.args.get('limit', 50, type=int)
    
    history = get_stock_history(item_id, limit)
    return jsonify(history)

# ============================================
# ANALYTICS API ROUTES
# ============================================

@app.route('/api/analytics/train', methods=['POST'])
def train_ml_model():
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    success = predictor.train_demand_predictor()
    return jsonify({
        'success': success,
        'message': 'Model trained successfully!' if success else 'Not enough data'
    })

@app.route('/api/analytics/predictions', methods=['GET'])
def get_predictions():
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    return jsonify(predictor.get_recommendations())

@app.route('/api/analytics/trends', methods=['GET'])
def get_trends():
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    days = request.args.get('days', 30, type=int)
    trends = analyze_sales_trends(days)
    return jsonify(trends if trends else {'message': 'No data available'})

@app.route('/api/analytics/peak-hours', methods=['GET'])
def get_peak_hours():
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    return jsonify(analyze_peak_hours())

@app.route('/api/analytics/category-performance', methods=['GET'])
def get_category_performance():
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    return jsonify(get_sales_by_category())

@app.route('/api/analytics/daily-stats', methods=['GET'])
def get_daily_statistics():
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    return jsonify(get_daily_stats())

@app.route('/api/analytics/monthly-stats', methods=['GET'])
def get_monthly_statistics():
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    return jsonify(get_monthly_stats())

@app.route('/api/analytics/chart-data', methods=['GET'])
def get_chart_data():
    """Get data for admin dashboard charts"""
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = sqlite3.connect(DATABASE)
        
        # Get last 30 days of data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        query = '''
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as order_count,
                SUM(total) as revenue
            FROM orders
            WHERE timestamp BETWEEN ? AND ?
            GROUP BY DATE(timestamp)
            ORDER BY date
        '''
        
        df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        conn.close()
        
        if len(df) == 0:
            return jsonify({
                'dates': [],
                'revenues': [],
                'orderCounts': []
            })
        
        return jsonify({
            'dates': df['date'].tolist(),
            'revenues': df['revenue'].tolist(),
            'orderCounts': df['order_count'].tolist()
        })
    except Exception as e:
        print(f"Error getting chart data: {e}")
        return jsonify({
            'dates': [],
            'revenues': [],
            'orderCounts': []
        })

if __name__ == '__main__':
    print("=" * 50)
    print("EKHAYA AFRICA RESTAURANT POS SYSTEM")
    print("=" * 50)
    print("Side Prices:")
    print("Uphuthu: +R20")
    print("Jeqe: +R30")
    print("=" * 50)
    print("Login Credentials:")
    print("Cashier: cashier / cash123")
    print("Kitchen: kitchen / cook123")
    print("Admin: admin / admin123")
    print("Puncher: puncher / stock123")
    print("=" * 50)
    app.run(debug=False, host='0.0.0.0', port=5000)