"""
HyperLocal Ride Booking - FINAL WORKING VERSION
"""

import streamlit as st
import sqlite3
import hashlib
import time
import random
import pandas as pd
from datetime import datetime

# ==================== DATABASE SETUP ====================

def init_db():
    """Initialize database with USERS"""
    conn = sqlite3.connect('hyperlocal.db')
    c = conn.cursor()
    
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        user_type TEXT NOT NULL,
        status TEXT DEFAULT 'approved',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        service_type TEXT NOT NULL,
        pickup_location TEXT NOT NULL,
        fare REAL NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    
    # ===== CREATE USERS - SIMPLE AND DIRECT =====
    # Delete all existing users
    c.execute("DELETE FROM users")
    
    # Admin
    admin_pass = hashlib.sha256('admin123'.encode()).hexdigest()
    c.execute("INSERT INTO users (username, password, full_name, phone, user_type, status) VALUES (?, ?, ?, ?, ?, ?)",
              ('admin', admin_pass, 'System Admin', '9999999999', 'admin', 'approved'))
    
    # Customer
    customer_pass = hashlib.sha256('customer123'.encode()).hexdigest()
    c.execute("INSERT INTO users (username, password, full_name, phone, user_type, status) VALUES (?, ?, ?, ?, ?, ?)",
              ('customer', customer_pass, 'Test Customer', '9876543210', 'customer', 'approved'))
    
    # Driver
    driver_pass = hashlib.sha256('driver123'.encode()).hexdigest()
    c.execute("INSERT INTO users (username, password, full_name, phone, user_type, status) VALUES (?, ?, ?, ?, ?, ?)",
              ('driver', driver_pass, 'Test Driver', '8765432109', 'driver', 'approved'))
    
    conn.commit()
    
    # Verify
    c.execute("SELECT username, user_type FROM users")
    print("✅ USERS CREATED:", c.fetchall())
    
    conn.close()

# ==================== AUTHENTICATION ====================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_user(username, password):
    """Simple login function"""
    conn = sqlite3.connect('hyperlocal.db')
    c = conn.cursor()
    hashed = hash_password(password)
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed))
    user = c.fetchone()
    conn.close()
    return user

# ==================== UI ====================

st.set_page_config(page_title="HyperLocal", page_icon="🚗", layout="wide")

# Custom CSS
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
</style>
""", unsafe_allow_html=True)

# ==================== SIDEBAR ====================

def show_sidebar():
    with st.sidebar:
        st.markdown("### 🚗 HyperLocal")
        st.markdown("---")
        
        if 'user' in st.session_state:
            st.markdown(f"### 👋 Welcome, {st.session_state.user[3]}")
            st.markdown(f"**Role:** {st.session_state.user[5].title()}")
            st.markdown("---")
            
            if st.session_state.user[5] == 'admin':
                menu = ["Dashboard", "Users"]
            else:
                menu = ["Dashboard", "Book Ride", "My Bookings"]
            
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

# ==================== ADMIN ====================

def admin_dashboard():
    st.markdown("<div class='header-gradient'><h1>📊 Admin Dashboard</h1></div>", unsafe_allow_html=True)
    
    conn = sqlite3.connect('hyperlocal.db')
    users = pd.read_sql("SELECT * FROM users", conn)
    conn.close()
    
    st.write("### 👥 Users")
    st.dataframe(users)

def admin_users():
    st.header("👥 Users")
    conn = sqlite3.connect('hyperlocal.db')
    users = pd.read_sql("SELECT * FROM users", conn)
    conn.close()
    st.dataframe(users)

# ==================== CUSTOMER ====================

def customer_dashboard():
    st.markdown("<div class='header-gradient'><h1>🏠 Customer Dashboard</h1></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚗 Book Ride"):
            st.session_state.page = "Book Ride"
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
        c.execute("INSERT INTO bookings (customer_id, service_type, pickup_location, fare) VALUES (?, ?, ?, ?)",
                 (st.session_state.user[0], service_type, pickup, fare))
        booking_id = c.lastrowid
        conn.commit()
        conn.close()
        st.success(f"✅ Ride booked! #{booking_id}")

def my_bookings():
    st.header("📋 My Bookings")
    conn = sqlite3.connect('hyperlocal.db')
    bookings = pd.read_sql("SELECT * FROM bookings WHERE customer_id = ?", conn, params=(st.session_state.user[0],))
    conn.close()
    
    if not bookings.empty:
        st.dataframe(bookings)
    else:
        st.info("No bookings")

# ==================== LOGIN ====================

def login_page():
    st.markdown("<div class='header-gradient'><h1>🔑 Login</h1></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class='credentials-box'>
            <strong>📝 Use these:</strong><br>
            👑 Admin: <code>admin</code> / <code>admin123</code><br>
            👤 Customer: <code>customer</code> / <code>customer123</code>
        </div>
        """, unsafe_allow_html=True)
        
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        user_type = st.selectbox("Login as", ["admin", "customer"])
        
        if st.button("Login", use_container_width=True):
            if not username or not password:
                st.error("❌ Please enter both")
                return
            
            user = login_user(username, password)
            
            if user is None:
                st.error("❌ Invalid username or password")
                return
            
            # Check if user type matches
            if user[5] == user_type:
                st.session_state.user = user
                st.success("✅ Login successful!")
                st.session_state.page = "Dashboard"
                st.rerun()
            else:
                st.error(f"❌ Wrong role. This user is '{user[5]}', not '{user_type}'")

# ==================== MAIN ====================

def main():
    # Initialize database with users
    init_db()
    
    # Session state
    if 'page' not in st.session_state:
        st.session_state.page = "Dashboard"
    
    # Sidebar
    show_sidebar()
    
    # Check login
    if 'user' not in st.session_state:
        login_page()
        return
    
    # Route
    user_type = st.session_state.user[5]
    
    if user_type == 'admin':
        if st.session_state.page == "Dashboard": admin_dashboard()
        elif st.session_state.page == "Users": admin_users()
        else: admin_dashboard()
    else:
        if st.session_state.page == "Dashboard": customer_dashboard()
        elif st.session_state.page == "Book Ride": book_ride()
        elif st.session_state.page == "My Bookings": my_bookings()
        else: customer_dashboard()

if __name__ == "__main__":
    main()
