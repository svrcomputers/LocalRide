import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import plotly.express as px
from datetime import datetime

# ==================== DATABASE SETUP ====================

def init_db():
    """Initialize database with forced admin"""
    conn = sqlite3.connect('hyperlocal.db')
    c = conn.cursor()
    
    # Create users table
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
    
    # Create bookings table
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
    
    # FORCE CREATE ADMIN - using direct SQL
    admin_pass = hashlib.sha256('admin123'.encode()).hexdigest()
    
    # Delete any existing admin
    c.execute("DELETE FROM users WHERE username = 'admin'")
    
    # Create admin
    c.execute("""INSERT INTO users (username, password, full_name, phone, user_type, status) 
                 VALUES (?, ?, ?, ?, ?, ?)""",
              ('admin', admin_pass, 'System Admin', '9999999999', 'admin', 'approved'))
    
    # Create customer
    customer_pass = hashlib.sha256('customer123'.encode()).hexdigest()
    c.execute("DELETE FROM users WHERE username = 'customer'")
    c.execute("""INSERT INTO users (username, password, full_name, phone, user_type, status) 
                 VALUES (?, ?, ?, ?, ?, ?)""",
              ('customer', customer_pass, 'Test Customer', '9876543210', 'customer', 'approved'))
    
    conn.commit()
    
    # Verify
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if c.fetchone():
        print("✅ Admin created successfully!")
    else:
        print("❌ Admin creation failed!")
    
    conn.close()

# ==================== AUTHENTICATION ====================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username, password):
    conn = sqlite3.connect('hyperlocal.db')
    c = conn.cursor()
    hashed = hash_password(password)
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed))
    user = c.fetchone()
    conn.close()
    return user

# ==================== UI ====================

def set_page_config():
    st.set_page_config(
        page_title="HyperLocal Ride Booking",
        page_icon="🚗",
        layout="wide"
    )
    
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
        .stButton > button:hover {
            background-color: #1557b0;
        }
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
                menu = ["Dashboard", "Users", "Bookings"]
            elif st.session_state.user[5] == 'customer':
                menu = ["Dashboard", "Book Ride", "My Bookings"]
            else:
                menu = ["Dashboard"]
            
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

# ==================== ADMIN FUNCTIONS ====================

def admin_dashboard():
    st.markdown("<div class='header-gradient'><h1>📊 Admin Dashboard</h1></div>", unsafe_allow_html=True)
    
    conn = sqlite3.connect('hyperlocal.db')
    
    col1, col2 = st.columns(2)
    
    with col1:
        total_users = pd.read_sql("SELECT COUNT(*) as count FROM users", conn)['count'][0]
        st.markdown(f"""
        <div class='metric-card'>
            <h3>👥 Total Users</h3>
            <h2>{total_users}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_bookings = pd.read_sql("SELECT COUNT(*) as count FROM bookings", conn)['count'][0]
        st.markdown(f"""
        <div class='metric-card'>
            <h3>📋 Total Bookings</h3>
            <h2>{total_bookings}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Show users
    st.subheader("👥 Users")
    users = pd.read_sql("SELECT id, username, full_name, user_type, status FROM users", conn)
    st.dataframe(users)
    
    conn.close()

def admin_users():
    st.header("👥 User Management")
    
    conn = sqlite3.connect('hyperlocal.db')
    users = pd.read_sql("SELECT id, username, full_name, user_type, status FROM users", conn)
    conn.close()
    
    st.dataframe(users)

def admin_bookings():
    st.header("📋 All Bookings")
    
    conn = sqlite3.connect('hyperlocal.db')
    bookings = pd.read_sql("SELECT * FROM bookings", conn)
    conn.close()
    
    if not bookings.empty:
        st.dataframe(bookings)
    else:
        st.info("No bookings yet")

# ==================== CUSTOMER FUNCTIONS ====================

def customer_dashboard():
    st.markdown("<div class='header-gradient'><h1>🏠 Customer Dashboard</h1></div>", unsafe_allow_html=True)
    
    conn = sqlite3.connect('hyperlocal.db')
    
    col1, col2 = st.columns(2)
    
    with col1:
        total_bookings = pd.read_sql("SELECT COUNT(*) as count FROM bookings WHERE customer_id = ?", 
                                    conn, params=(st.session_state.user[0],))['count'][0]
        st.markdown(f"""
        <div class='metric-card'>
            <h3>📋 My Bookings</h3>
            <h2>{total_bookings}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if st.button("🚗 Book a Ride", use_container_width=True):
            st.session_state.page = "Book Ride"
            st.rerun()
    
    # Recent bookings
    st.subheader("📋 Your Recent Bookings")
    recent = pd.read_sql("""
        SELECT id, service_type, pickup_location, fare, status, created_at
        FROM bookings 
        WHERE customer_id = ?
        ORDER BY created_at DESC 
        LIMIT 5
    """, conn, params=(st.session_state.user[0],))
    
    if not recent.empty:
        st.dataframe(recent)
    else:
        st.info("No bookings yet")
    
    conn.close()

def book_ride():
    st.markdown("<div class='header-gradient'><h1>🚗 Book a Ride</h1></div>", unsafe_allow_html=True)
    
    service_type = st.selectbox("Select Vehicle", ["Bike", "Auto", "Cab"])
    pickup = st.text_input("Pickup Location", "Your Location")
    dropoff = st.text_input("Dropoff Location", "Destination")
    
    # Fare calculator
    import random
    distance = random.uniform(2, 15)
    base_fares = {"Bike": 20, "Auto": 35, "Cab": 60}
    fare = base_fares[service_type] + (distance * 8)
    
    st.markdown(f"""
    <div style='background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;'>
        <h4>Fare Estimate</h4>
        <p>Distance: {distance:.1f} km</p>
        <p><strong>Estimated Fare: ₹{fare:.0f}</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚗 Book Now", use_container_width=True):
        conn = sqlite3.connect('hyperlocal.db')
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO bookings (customer_id, service_type, pickup_location, fare, status)
            VALUES (?, ?, ?, ?, ?)
        """, (st.session_state.user[0], service_type, pickup, fare, 'pending'))
        
        booking_id = c.lastrowid
        conn.commit()
        conn.close()
        
        st.success(f"✅ Ride booked successfully! Booking ID: #{booking_id}")

def my_bookings():
    st.header("📋 My Bookings")
    
    conn = sqlite3.connect('hyperlocal.db')
    bookings = pd.read_sql("""
        SELECT id, service_type, pickup_location, fare, status, created_at
        FROM bookings 
        WHERE customer_id = ?
        ORDER BY created_at DESC
    """, conn, params=(st.session_state.user[0],))
    conn.close()
    
    if not bookings.empty:
        st.dataframe(bookings)
    else:
        st.info("No bookings found")

# ==================== LOGIN/REGISTER ====================

def login_page():
    st.markdown("<div class='header-gradient'><h1>🔑 Login</h1></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class='credentials-box'>
            <strong>📝 Test Credentials:</strong><br>
            👑 Admin: <code>admin</code> / <code>admin123</code><br>
            👤 Customer: <code>customer</code> / <code>customer123</code>
        </div>
        """, unsafe_allow_html=True)
        
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        user_type = st.selectbox("Login as", ["admin", "customer"])
        
        if st.button("Login", use_container_width=True):
            if not username or not password:
                st.error("❌ Please enter both username and password")
            else:
                user = authenticate_user(username, password)
                if user:
                    if user[5] == user_type:
                        st.session_state.user = user
                        st.success("✅ Login successful!")
                        st.session_state.page = "Dashboard"
                        st.rerun()
                    else:
                        st.error("❌ User type mismatch. Please select the correct role.")
                else:
                    st.error("❌ Invalid username or password")

# ==================== MAIN APP ====================

def main():
    """Main application entry point"""
    # Initialize database
    init_db()
    
    # Set page config
    set_page_config()
    
    # Initialize session state
    if 'page' not in st.session_state:
        st.session_state.page = "Dashboard"
    
    # Show sidebar
    show_sidebar()
    
    # Check if user is logged in
    if 'user' not in st.session_state:
        login_page()
        return
    
    # Main content routing
    user_type = st.session_state.user[5]
    
    if user_type == 'admin':
        if st.session_state.page == "Dashboard":
            admin_dashboard()
        elif st.session_state.page == "Users":
            admin_users()
        elif st.session_state.page == "Bookings":
            admin_bookings()
        else:
            admin_dashboard()
    
    elif user_type == 'customer':
        if st.session_state.page == "Dashboard":
            customer_dashboard()
        elif st.session_state.page == "Book Ride":
            book_ride()
        elif st.session_state.page == "My Bookings":
            my_bookings()
        else:
            customer_dashboard()
    
    else:
        st.info("Welcome to HyperLocal!")

if __name__ == "__main__":
    main()
