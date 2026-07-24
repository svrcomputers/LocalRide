"""
Hyper Local Ride Booking Application - FIXED VERSION
"""

import streamlit as st
import sqlite3
import hashlib
import time
import random
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
import plotly.express as px

# ==================== DATABASE SETUP ====================

def init_db():
    """Initialize SQLite database"""
    try:
        conn = sqlite3.connect('hyperlocal.db')
        c = conn.cursor()
        
        # Create tables
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            user_type TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            vehicle_type TEXT NOT NULL,
            vehicle_number TEXT NOT NULL,
            license_number TEXT NOT NULL,
            rating REAL DEFAULT 0.0,
            total_rides INTEGER DEFAULT 0,
            earnings REAL DEFAULT 0.0,
            is_available BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            driver_id INTEGER,
            service_type TEXT NOT NULL,
            pickup_location TEXT NOT NULL,
            dropoff_location TEXT,
            fare REAL NOT NULL,
            distance REAL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            rating INTEGER,
            FOREIGN KEY (customer_id) REFERENCES users (id),
            FOREIGN KEY (driver_id) REFERENCES users (id)
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS parcels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            parcel_type TEXT NOT NULL,
            weight REAL NOT NULL,
            receiver_name TEXT NOT NULL,
            receiver_phone TEXT NOT NULL,
            FOREIGN KEY (booking_id) REFERENCES bookings (id)
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id INTEGER NOT NULL,
            service_type TEXT NOT NULL,
            price REAL NOT NULL,
            is_available BOOLEAN DEFAULT 1,
            FOREIGN KEY (provider_id) REFERENCES users (id)
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS service_bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            booking_date DATE NOT NULL,
            booking_time TIME NOT NULL,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (service_id) REFERENCES services (id),
            FOREIGN KEY (customer_id) REFERENCES users (id)
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS wallet (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            transaction_type TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )''')
        
        conn.commit()
        
        # ===== FORCE CREATE USERS =====
        admin_pass = hashlib.sha256('admin123'.encode()).hexdigest()
        customer_pass = hashlib.sha256('customer123'.encode()).hexdigest()
        driver_pass = hashlib.sha256('driver123'.encode()).hexdigest()
        
        # Delete existing
        c.execute("DELETE FROM users WHERE username IN ('admin', 'customer', 'driver')")
        
        # Create admin
        c.execute("""INSERT INTO users (username, password, full_name, phone, user_type, status) 
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  ('admin', admin_pass, 'System Admin', '9999999999', 'admin', 'approved'))
        
        # Create customer
        c.execute("""INSERT INTO users (username, password, full_name, phone, user_type, status) 
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  ('customer', customer_pass, 'Test Customer', '9876543210', 'customer', 'approved'))
        
        # Create driver
        c.execute("""INSERT INTO users (username, password, full_name, phone, user_type, status) 
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  ('driver', driver_pass, 'Test Driver', '8765432109', 'driver', 'approved'))
        
        # Create driver profile
        c.execute("SELECT id FROM users WHERE username = 'driver'")
        driver_user = c.fetchone()
        if driver_user:
            driver_id = driver_user[0]
            c.execute("DELETE FROM drivers WHERE user_id = ?", (driver_id,))
            c.execute("""INSERT INTO drivers (user_id, vehicle_type, vehicle_number, license_number, is_available) 
                         VALUES (?, ?, ?, ?, ?)""",
                      (driver_id, 'bike', 'TN01AB1234', 'DL1234567890', 1))
        
        conn.commit()
        
        # Verify
        c.execute("SELECT id, username, user_type, status FROM users")
        print("✅ Users created:", c.fetchall())
        
        conn.close()
        return True
    except Exception as e:
        print(f"Database error: {e}")
        return False

# ==================== AUTHENTICATION ====================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username, password):
    try:
        conn = sqlite3.connect('hyperlocal.db')
        c = conn.cursor()
        hashed = hash_password(password)
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed))
        user = c.fetchone()
        conn.close()
        return user
    except Exception as e:
        print(f"Auth error: {e}")
        return None

# ==================== UI ====================

def set_page_config():
    st.set_page_config(page_title="HyperLocal", page_icon="🚗", layout="wide")
    
    st.markdown("""
    <style>
        .stButton > button {
            background-color: #1a73e8;
            color: white;
            border-radius: 25px;
            padding: 10px 25px;
            border: none;
            font-weight: 600;
            width: 100%;
        }
        .stButton > button:hover { background-color: #1557b0; }
        .metric-card {
            background: linear-gradient(135deg, #1a73e8, #0d47a1);
            padding: 20px;
            border-radius: 15px;
            color: white;
            text-align: center;
        }
        .header-gradient {
            background: linear-gradient(135deg, #1a73e8, #0d47a1);
            padding: 20px;
            border-radius: 15px;
            color: white;
            margin-bottom: 30px;
        }
        .credentials-box {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
            border: 1px solid #e9ecef;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            border-left: 4px solid #1a73e8;
        }
        .login-container {
            max-width: 450px;
            margin: 0 auto;
            padding: 30px;
            background: white;
            border-radius: 15px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
    </style>
    """, unsafe_allow_html=True)

def show_sidebar():
    with st.sidebar:
        st.markdown("### 🚗 HyperLocal")
        st.markdown("---")
        
        if 'user' in st.session_state:
            st.markdown(f"### 👋 Welcome, {st.session_state.user[3]}")
            st.markdown(f"**Role:** {st.session_state.user[5].title()}")
            st.markdown("---")
            
            if st.session_state.user[5] == 'admin':
                menu = ["Dashboard", "Users", "Drivers", "Bookings"]
            elif st.session_state.user[5] == 'driver':
                menu = ["Dashboard", "My Rides", "Earnings"]
            else:
                menu = ["Dashboard", "Book Ride", "Parcel Delivery", "Local Services", "My Bookings", "Wallet"]
            
            for item in menu:
                if st.button(item, key=f"nav_{item}"):
                    st.session_state.page = item
                    st.rerun()
            
            st.markdown("---")
            if st.button("🚪 Logout"):
                for key in ['user', 'page']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        else:
            if st.button("🔑 Login"):
                st.session_state.page = "Login"
                st.rerun()
            if st.button("📝 Register"):
                st.session_state.page = "Register"
                st.rerun()

# ==================== ADMIN FUNCTIONS ====================

def admin_dashboard():
    st.markdown("<div class='header-gradient'><h1>📊 Admin Dashboard</h1></div>", unsafe_allow_html=True)
    
    conn = sqlite3.connect('hyperlocal.db')
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_users = pd.read_sql("SELECT COUNT(*) as count FROM users", conn)['count'][0]
        st.markdown(f"""<div class='metric-card'><h3>👥 Users</h3><h2>{total_users}</h2></div>""", unsafe_allow_html=True)
    
    with col2:
        total_drivers = pd.read_sql("SELECT COUNT(*) as count FROM users WHERE user_type = 'driver'", conn)['count'][0]
        st.markdown(f"""<div class='metric-card'><h3>🚗 Drivers</h3><h2>{total_drivers}</h2></div>""", unsafe_allow_html=True)
    
    with col3:
        total_bookings = pd.read_sql("SELECT COUNT(*) as count FROM bookings", conn)['count'][0]
        st.markdown(f"""<div class='metric-card'><h3>📋 Bookings</h3><h2>{total_bookings}</h2></div>""", unsafe_allow_html=True)
    
    conn.close()

def admin_users():
    st.header("👥 Users")
    conn = sqlite3.connect('hyperlocal.db')
    users = pd.read_sql("SELECT id, username, full_name, user_type, status FROM users", conn)
    conn.close()
    st.dataframe(users)

def admin_drivers():
    st.header("🚗 Drivers")
    conn = sqlite3.connect('hyperlocal.db')
    drivers = pd.read_sql("SELECT * FROM drivers", conn)
    conn.close()
    st.dataframe(drivers)

def admin_bookings():
    st.header("📋 Bookings")
    conn = sqlite3.connect('hyperlocal.db')
    bookings = pd.read_sql("SELECT * FROM bookings ORDER BY created_at DESC", conn)
    conn.close()
    st.dataframe(bookings)

# ==================== CUSTOMER FUNCTIONS ====================

def customer_dashboard():
    st.markdown("<div class='header-gradient'><h1>🏠 Customer Dashboard</h1></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🚗 Book Ride"):
            st.session_state.page = "Book Ride"
            st.rerun()
    with col2:
        if st.button("📦 Parcel"):
            st.session_state.page = "Parcel Delivery"
            st.rerun()
    with col3:
        if st.button("🔧 Services"):
            st.session_state.page = "Local Services"
            st.rerun()
    
    conn = sqlite3.connect('hyperlocal.db')
    recent = pd.read_sql("""
        SELECT id, service_type, pickup_location, fare, status, created_at
        FROM bookings WHERE customer_id = ?
        ORDER BY created_at DESC LIMIT 5
    """, conn, params=(st.session_state.user[0],))
    conn.close()
    
    st.subheader("📋 Recent Bookings")
    if not recent.empty:
        st.dataframe(recent)
    else:
        st.info("No bookings yet")

def book_ride():
    st.markdown("<div class='header-gradient'><h1>🚗 Book a Ride</h1></div>", unsafe_allow_html=True)
    
    service_type = st.selectbox("Vehicle", ["Bike", "Auto", "Cab"])
    pickup = st.text_input("Pickup Location", "Your Location")
    dropoff = st.text_input("Dropoff Location", "Destination")
    
    distance = random.uniform(2, 15)
    base_fares = {"Bike": 20, "Auto": 35, "Cab": 60}
    fare = base_fares[service_type] + (distance * 8)
    
    st.markdown(f"""
    <div class='card'>
        <h4>Fare Estimate</h4>
        <p>Distance: {distance:.1f} km</p>
        <p><strong>₹{fare:.0f}</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚗 Book Now"):
        conn = sqlite3.connect('hyperlocal.db')
        c = conn.cursor()
        
        c.execute("SELECT id FROM users WHERE user_type = 'driver' AND status = 'approved' LIMIT 1")
        driver = c.fetchone()
        
        if driver:
            c.execute("""INSERT INTO bookings (customer_id, driver_id, service_type, pickup_location, 
                         dropoff_location, fare, distance, status)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                     (st.session_state.user[0], driver[0], service_type, pickup, dropoff, fare, distance, 'pending'))
            
            booking_id = c.lastrowid
            conn.commit()
            conn.close()
            st.success(f"✅ Ride booked! #{booking_id}")
        else:
            st.warning("No drivers available")
            conn.close()

def parcel_delivery():
    st.markdown("<div class='header-gradient'><h1>📦 Parcel Delivery</h1></div>", unsafe_allow_html=True)
    
    parcel_type = st.selectbox("Parcel Type", ["Document", "Package", "Food", "Medicine"])
    weight = st.number_input("Weight (kg)", 0.1, 50.0, 1.0)
    receiver_name = st.text_input("Receiver Name")
    receiver_phone = st.text_input("Receiver Phone")
    pickup = st.text_input("Pickup Location")
    dropoff = st.text_input("Dropoff Location")
    
    delivery_charge = 30 + (random.uniform(1, 10) * 5) + (weight * 10)
    
    st.markdown(f"""
    <div class='card'>
        <h4>Delivery Charge</h4>
        <p><strong>₹{delivery_charge:.0f}</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("📦 Book Delivery"):
        conn = sqlite3.connect('hyperlocal.db')
        c = conn.cursor()
        c.execute("""INSERT INTO bookings (customer_id, service_type, pickup_location, dropoff_location, fare, status)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                 (st.session_state.user[0], 'Parcel', pickup, dropoff, delivery_charge, 'pending'))
        booking_id = c.lastrowid
        c.execute("""INSERT INTO parcels (booking_id, parcel_type, weight, receiver_name, receiver_phone)
                     VALUES (?, ?, ?, ?, ?)""",
                 (booking_id, parcel_type, weight, receiver_name, receiver_phone))
        conn.commit()
        conn.close()
        st.success(f"✅ Parcel booked! #{booking_id}")

def local_services():
    st.markdown("<div class='header-gradient'><h1>🔧 Local Services</h1></div>", unsafe_allow_html=True)
    
    services_list = ["Electrician", "Plumber", "AC Repair", "Laptop Repair", "Mobile Repair"]
    service_type = st.selectbox("Select Service", services_list)
    
    base_prices = {"Electrician": 300, "Plumber": 350, "AC Repair": 500, "Laptop Repair": 400, "Mobile Repair": 250}
    price = base_prices.get(service_type, 300)
    
    service_date = st.date_input("Date", min_value=datetime.now().date())
    service_time = st.time_input("Time", value=datetime.now().time())
    
    st.markdown(f"""
    <div class='card'>
        <h3>₹{price}</h3>
        <p>Base price for {service_type}</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔧 Book Service"):
        conn = sqlite3.connect('hyperlocal.db')
        c = conn.cursor()
        c.execute("SELECT id FROM services WHERE service_type = ? LIMIT 1", (service_type,))
        service = c.fetchone()
        
        if not service:
            c.execute("INSERT INTO services (provider_id, service_type, price) VALUES (?, ?, ?)",
                     (1, service_type, price))
            service_id = c.lastrowid
        else:
            service_id = service[0]
        
        c.execute("""INSERT INTO service_bookings (service_id, customer_id, booking_date, booking_time, status)
                     VALUES (?, ?, ?, ?, ?)""",
                 (service_id, st.session_state.user[0], service_date, service_time, 'confirmed'))
        conn.commit()
        conn.close()
        st.success(f"✅ {service_type} booked!")

def my_bookings():
    st.header("📋 My Bookings")
    
    conn = sqlite3.connect('hyperlocal.db')
    bookings = pd.read_sql("""
        SELECT id, service_type, pickup_location, fare, status, created_at
        FROM bookings WHERE customer_id = ?
        ORDER BY created_at DESC
    """, conn, params=(st.session_state.user[0],))
    conn.close()
    
    if not bookings.empty:
        st.dataframe(bookings)
    else:
        st.info("No bookings")

def customer_wallet():
    st.header("💰 My Wallet")
    
    conn = sqlite3.connect('hyperlocal.db')
    balance = pd.read_sql("""
        SELECT COALESCE(SUM(CASE WHEN transaction_type = 'credit' THEN amount ELSE -amount END), 0) as balance
        FROM wallet WHERE user_id = ?
    """, conn, params=(st.session_state.user[0],))['balance'][0]
    conn.close()
    
    st.markdown(f"""<div class='metric-card'><h3>💰 Balance</h3><h2>₹{balance:.2f}</h2></div>""", unsafe_allow_html=True)
    
    amount = st.number_input("Add Money (₹)", 1.0, 10000.0, 100.0)
    if st.button("Add Money"):
        conn = sqlite3.connect('hyperlocal.db')
        c = conn.cursor()
        c.execute("INSERT INTO wallet (user_id, amount, transaction_type, description) VALUES (?, ?, ?, ?)",
                 (st.session_state.user[0], amount, 'credit', 'Added money'))
        conn.commit()
        conn.close()
        st.success(f"₹{amount} added!")
        st.rerun()

# ==================== DRIVER FUNCTIONS ====================

def driver_dashboard():
    st.markdown("<div class='header-gradient'><h1>🚗 Driver Dashboard</h1></div>", unsafe_allow_html=True)
    
    conn = sqlite3.connect('hyperlocal.db')
    driver = pd.read_sql("SELECT * FROM drivers WHERE user_id = ?", conn, params=(st.session_state.user[0],))
    conn.close()
    
    if not driver.empty:
        d = driver.iloc[0]
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""<div class='metric-card'><h3>⭐ Rating</h3><h2>{d['rating']:.1f}</h2></div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class='metric-card'><h3>🚗 Rides</h3><h2>{d['total_rides']}</h2></div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div class='metric-card'><h3>💰 Earnings</h3><h2>₹{d['earnings']:.0f}</h2></div>""", unsafe_allow_html=True)

def driver_rides():
    st.header("📋 My Rides")
    conn = sqlite3.connect('hyperlocal.db')
    rides = pd.read_sql("SELECT * FROM bookings WHERE driver_id = ?", conn, params=(st.session_state.user[0],))
    conn.close()
    st.dataframe(rides)

def driver_earnings():
    st.header("💰 Earnings")
    st.info("Earnings summary coming soon")

# ==================== LOGIN/REGISTER ====================

def login_page():
    st.markdown("<div class='header-gradient'><h1>🔑 Login</h1></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class='credentials-box'>
            <strong>📝 Test Credentials:</strong><br>
            👑 Admin: <code>admin</code> / <code>admin123</code><br>
            👤 Customer: <code>customer</code> / <code>customer123</code><br>
            🚗 Driver: <code>driver</code> / <code>driver123</code>
        </div>
        """, unsafe_allow_html=True)
        
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        user_type = st.selectbox("Login as", ["admin", "customer", "driver"])
        
        if st.button("Login", use_container_width=True):
            if not username or not password:
                st.error("❌ Please enter both")
            else:
                user = authenticate_user(username, password)
                if user:
                    if user[5] == user_type:
                        st.session_state.user = user
                        st.success("✅ Login successful!")
                        st.session_state.page = "Dashboard"
                        st.rerun()
                    else:
                        st.error(f"❌ User type mismatch. User is '{user[5]}', you selected '{user_type}'")
                else:
                    st.error("❌ Invalid credentials")

def register_page():
    st.markdown("<div class='header-gradient'><h1>📝 Register</h1></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        full_name = st.text_input("Full Name")
        username = st.text_input("Username")
        phone = st.text_input("Phone")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        user_type = st.selectbox("Register as", ["customer", "driver"])
        
        if st.button("Register", use_container_width=True):
            if password != confirm:
                st.error("❌ Passwords don't match")
            elif len(password) < 6:
                st.error("❌ Password must be 6+ characters")
            else:
                success, result = register_user(username, password, full_name, phone, email, user_type)
                if success:
                    st.success("✅ Registered! You can now login.")
                else:
                    st.error(f"❌ {result}")

# ==================== MAIN APP ====================

def main():
    # Initialize database
    init_db()
    
    # Set page config
    set_page_config()
    
    # Initialize session state
    if 'page' not in st.session_state:
        st.session_state.page = "Dashboard"
    
    # Show sidebar
    show_sidebar()
    
    # Check login
    if 'user' not in st.session_state:
        if st.session_state.page == "Register":
            register_page()
        else:
            login_page()
        return
    
    # Route based on user type
    user_type = st.session_state.user[5]
    
    if user_type == 'admin':
        if st.session_state.page == "Dashboard": admin_dashboard()
        elif st.session_state.page == "Users": admin_users()
        elif st.session_state.page == "Drivers": admin_drivers()
        elif st.session_state.page == "Bookings": admin_bookings()
        else: admin_dashboard()
    
    elif user_type == 'driver':
        if st.session_state.page == "Dashboard": driver_dashboard()
        elif st.session_state.page == "My Rides": driver_rides()
        elif st.session_state.page == "Earnings": driver_earnings()
        else: driver_dashboard()
    
    else:
        if st.session_state.page == "Dashboard": customer_dashboard()
        elif st.session_state.page == "Book Ride": book_ride()
        elif st.session_state.page == "Parcel Delivery": parcel_delivery()
        elif st.session_state.page == "Local Services": local_services()
        elif st.session_state.page == "My Bookings": my_bookings()
        elif st.session_state.page == "Wallet": customer_wallet()
        else: customer_dashboard()

if __name__ == "__main__":
    main()
