# 🍖 Ekhaya Africa Restaurant POS System

A comprehensive Point of Sale (POS) system built for a traditional South African Shisanyama restaurant, featuring multi-role access, inventory management, ML-powered analytics, and real-time order tracking.

## 🎯 Live Demo

**[https://pos-system-1-sb2v.onrender.com](#)**

### Demo Credentials

| Role | Username | Password | Access Level |
|------|----------|----------|--------------|
| 👨‍💼 Admin | `admin` | `admin123` | Full system access, analytics, reports |
| 💰 Cashier | `cashier` | `cash123` | Create orders, process payments |
| 👨‍🍳 Kitchen | `kitchen` | `cook123` | View and complete orders |
| 📦 Puncher | `puncher` | `stock123` | Manage inventory and menu items |

## ✨ Features

### 🔐 Multi-Role Authentication System
- **Admin Dashboard**: Complete oversight with analytics and reporting
- **Cashier Interface**: Quick order creation and payment processing
- **Kitchen Display**: Real-time order management
- **Stock Management**: Inventory control and menu updates

### 📊 Advanced Analytics (ML-Powered)
- Sales trend analysis with predictive modeling
- Peak hours identification
- Demand forecasting using Random Forest algorithms
- Category performance tracking
- Revenue and order insights

### 🍽️ Smart Menu System
- Dynamic pricing with customizable side options
- Meat items with automatic side selection (Uphuthu +R20, Jeqe +R30)
- Stock tracking with low-inventory alerts
- Category-based organization (Meats, Sides, Drinks)

### 📦 Inventory Management
- Real-time stock updates
- Comprehensive stock history tracking
- Automated stock deduction on orders
- Restock notifications and management

### 💳 Order Processing
- Multiple payment methods (Cash, Card)
- Order status tracking (Pending → Ready)
- Estimated preparation times
- Customer order history

### 📈 Reporting System
- Daily sales reports
- Monthly revenue analysis
- Popular items tracking
- Category-wise sales breakdown

## 🛠️ Technology Stack

### Backend
- **Python 3.11** - Core programming language
- **Flask 3.0.0** - Web framework
- **SQLite** - Database management
- **Gunicorn** - WSGI HTTP Server for production

### Data Science & ML
- **Pandas 2.1.4** - Data manipulation and analysis
- **NumPy 1.26.2** - Numerical computing
- **Scikit-learn 1.3.2** - Machine learning algorithms

### Frontendw
- **HTML5/CSS3** - Modern responsive UI
- **JavaScript** - Interactive client-side functionality
- **Fetch API** - Asynchronous data operations

## 📁 Project Structure

```
shisanyama/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── shisanyama.db              # SQLite database (auto-generated)
├── static/                    # Static assets
│   ├── admin.css
│   ├── cashier.css
│   ├── kitchen.css
│   ├── puncher.css
│   ├── daily.css
│   └── monthly.css
├── templates/                 # HTML templates
│   ├── login.html            # Login page
│   ├── cashier.html          # Cashier interface
│   ├── kitchen.html          # Kitchen display
│   ├── admin.html            # Admin dashboard
│   ├── puncher.html          # Stock management
│   ├── daily.html            # Daily reports
│   └── monthly.html          # Monthly reports
└── README.md                 # This file
```

## 🚀 Installation & Setup

### Prerequisites
- Python 3.11 or higher
- pip (Python package manager)
- Git

### Local Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/shisanyama-pos.git
cd shisanyama-pos
```

2. **Create virtual environment**
```bash
python -m venv env

# Windows
env\Scripts\activate

# Mac/Linux
source env/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the application**
```bash
python app.py
python -m flask run
```

5. **Access the application**
```
Open your browser and navigate to: http://localhost:5000
```

## 🌐 Deployment to Render

### Step 1: Prepare for Deployment

Ensure these files exist in your project root:
- `requirements.txt` ✅
- `app.py` with `debug=False` ✅

### Step 2: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit - POS System"
git remote add origin https://github.com/YOUR_USERNAME/shisanyama-pos.git
git push -u origin main
```

### Step 3: Deploy on Render

1. Go to [Render.com](https://render.com)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `shisanyama-pos`
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
5. Click **"Create Web Service"**

### Step 4: Set Environment Variables (Optional)

In Render Dashboard → Environment:
```
SECRET_KEY=your-secret-key-here
```

## 📚 API Documentation

### Authentication Endpoints

#### POST `/login`
Login user
```json
{
  "username": "cashier",
  "password": "cash123"
}
```

#### GET `/logout`
Logout current user

### Order Management

#### GET `/api/orders`
Get all orders (requires authentication)

#### POST `/api/orders`
Create new order (cashier only)
```json
{
  "customerName": "John Doe",
  "items": [
    {
      "id": 1,
      "name": "Boiled Beef",
      "price": 140,
      "quantity": 1,
      "side_option": "Uphuthu"
    }
  ],
  "total": 140,
  "paymentMethod": "cash"
}
```

#### PUT `/api/orders/:id/complete`
Mark order as complete (kitchen only)

### Menu & Inventory

#### GET `/api/menu`
Get all menu items

#### POST `/api/puncher/menu`
Add new menu item (puncher only)

#### PUT `/api/puncher/stock/:id`
Update stock quantity (puncher only)

### Analytics

#### GET `/api/analytics/daily-stats`
Get today's statistics

#### GET `/api/analytics/monthly-stats`
Get current month's statistics

#### GET `/api/analytics/peak-hours`
Get peak business hours

#### POST `/api/analytics/train`
Train ML prediction model

## 🎨 Features Showcase

### 1. Cashier Interface
- Quick menu item selection
- Side option selection for meat items
- Real-time total calculation
- Multiple payment methods
- Order confirmation

### 2. Kitchen Display System
- Live order queue
- Order details with sides
- One-click order completion
- Preparation time tracking

### 3. Admin Analytics Dashboard
- Revenue charts and graphs
- Sales trends visualization
- ML-powered demand predictions
- Category performance analysis
- Popular items ranking

### 4. Stock Management (Puncher)
- Add/Edit/Delete menu items
- Bulk stock updates
- Stock history tracking
- Low stock alerts

## 🔒 Security Features

- Session-based authentication
- Role-based access control (RBAC)
- Environment variable support for secrets
- SQL injection prevention (parameterized queries)
- CSRF protection ready

## 🤖 Machine Learning Features

The system uses **Random Forest Regression** to:
- Predict demand by category
- Analyze sales patterns
- Identify peak business hours
- Generate stocking recommendations
- Forecast future inventory needs

## 📱 Responsive Design

The application is fully responsive and works seamlessly on:
- 💻 Desktop computers
- 📱 Tablets
- 📱 Mobile phones

## 🐛 Known Issues & Limitations

- SQLite database resets on Render free tier after inactivity
- ML model requires at least 10 completed orders to train
- No password encryption (for demo purposes)
- Single-location support only

## 🔮 Future Enhancements

- [ ] PostgreSQL integration for persistent storage
- [ ] Password hashing and enhanced security
- [ ] Multi-location support
- [ ] Customer loyalty program
- [ ] Email/SMS order notifications
- [ ] Receipt printing functionality
- [ ] Advanced reporting and exports
- [ ] Mobile app (React Native)
- [ ] Table management system
- [ ] Online ordering integration

## 👨‍💻 Author

**Andile Vuyiswa Ntshangase**

- Portfolio: [https://main-portfolio-one-beige.vercel.app/home](https://main-portfolio-one-beige.vercel.app/home)
- GitHub: [@0698113787](https://github.com/0698113787)

## 🙏 Acknowledgments

- Built with ❤️ for Ekhaya Africa Restaurant
- Inspired by traditional South African Shisanyama culture
- Thanks to the Flask and Python communities

## 📞 Support

For support, email vuyiswaandile176@gmail.com.

---
