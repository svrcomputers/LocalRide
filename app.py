"""
HyperLocal Ride Booking - FINAL WORKING VERSION
Uses Streamlit Secrets for authentication
"""

import streamlit as st
import sqlite3
import hashlib
import random
import pandas as pd

# ==================== DATABASE ====================

def init_db():
    """Initialize database"""
    conn = sqlite3.connect('hyperlocal.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        user_type TEXT NOT NULL,
        status TEXT DEFAULT 'approved'
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
    
    # Check if users exist
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    
    if count == 0:
        # Create users from secrets or defaults
        try:
            admin_user = st.secrets["admin"]["username"]
            admin_pass = st.secrets["admin"]["password"]
        except:
            admin_user = "admin"
            admin_pass = "admin123"
        
        hashed = hashlib.sha256(admin_pass.encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, full_name, phone, user_type, status) VALUES (?, ?, ?, ?, ?, ?)",
                  (admin_user, hashed, 'System Admin', '9999999999', 'admin', 'approved'))
        
        # Also create customer
        customer_pass = hashlib.sha256('customer123'.encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, full_name, phone, user_type, status) VALUES (?, ?, ?, ?, ?, ?)",
                  ('customer', customer_pass, 'Test Customer', '9876543210', 'customer', 'approved'))
        
        conn.commit()
        print(f"✅ Admin '{admin_user}' created!")
    
    conn.close()

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
        
        # If not found in DB, check secrets
        if user is None:
            try:
                if username == st.secrets["admin"]["username"] and password == st.secrets["admin"]["password"]:
                    # Create user in DB
                    conn = sqlite3.connect('hyperlocal.db')
                    c = conn.cursor()
                    hashed = hash_password(password)
                    c.execute("INSERT INTO users (username, password, full_name, phone, user_type, status) VALUES (?, ?, ?, ?, ?, ?)",
                              (username, hashed, 'System Admin', '9999999999', 'admin', 'approved'))
                    conn.commit()
                    conn.close()
                    
                    # Return the user
                    conn = sqlite3.connect('hyperlocal.db')
                    c = conn.cursor()
                    c.execute("SELECT * FROM users WHERE username = ?", (username,))
                    user = c.fetchone()
                    conn.close()
            except:
                pass
        
        return user
    except Exception as e:
        print(f"Auth error: {e}")
        return None

# ==================== UI ====================

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
    .metric-card {
        background: linear-gradient(135deg, #1a73e8, #0d47a1);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
    }
    .card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 10px 0;
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

            if st.button("📊 Dashboard"):
                st.session_state.page = "Dashboard"
                st.rerun()
            if st.button("🚗 Book Ride"):
                st.session_state.page = "Book Ride"
                st.rerun()
            if st.button("📋 My Bookings"):
                st.session_state.page = "My Bookings"
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
    bookings = pd.read_sql("SELECT * FROM bookings", conn)
    conn.close()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"<div class='metric-card'><h3>👥 Users</h3><h2>{len(users)}</h2></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-card'><h3>📋 Bookings</h3><h2>{len(bookings)}</h2></div>", unsafe_allow_html=True)

    st.subheader("👥 All Users")
    st.dataframe(users)

# ==================== CUSTOMER ====================

def customer_dashboard():
    st.markdown("<div class='header-gradient'><h1>🏠 Customer Dashboard</h1></div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚗 Book a Ride", use_container_width=True):
            st.session_state.page = "Book Ride"
            st.rerun()

    conn = sqlite3.connect('hyperlocal.db')
    bookings = pd.read_sql("SELECT * FROM bookings WHERE customer_id = ? ORDER BY created_at DESC LIMIT 5",
                          conn, params=(st.session_state.user[0],))
    conn.close()

    st.subheader("📋 Recent Bookings")
    if not bookings.empty:
        st.dataframe(bookings)
    else:
        st.info("No bookings yet")

def book_ride():
    st.markdown("<div class='header-gradient'><h1>🚗 Book a Ride</h1></div>", unsafe_allow_html=True)

    service_type = st.selectbox("Select Vehicle", ["Bike", "Auto", "Cab"])
    pickup = st.text_input("Pickup Location", "Your Location")
    dropoff = st.text_input("Dropoff Location", "Destination")

    distance = random.uniform(2, 15)
    base_fares = {"Bike": 20, "Auto": 35, "Cab": 60}
    fare = base_fares[service_type] + (distance * 8)

    st.markdown(f"""
    <div class='card'>
        <h4>Fare Estimate</h4>
        <p>Distance: {distance:.1f} km</p>
        <p><strong>Estimated Fare: ₹{fare:.0f}</strong></p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚗 Book Now", use_container_width=True):
        conn = sqlite3.connect('hyperlocal.db')
        c = conn.cursor()
        c.execute("INSERT INTO bookings (customer_id, service_type, pickup_location, fare) VALUES (?, ?, ?, ?)",
                 (st.session_state.user[0], service_type, pickup, fare))
        booking_id = c.lastrowid
        conn.commit()
        conn.close()
        st.success(f"✅ Ride booked! Booking ID: #{booking_id}")

def my_bookings():
    st.header("📋 My Bookings")
    conn = sqlite3.connect('hyperlocal.db')
    bookings = pd.read_sql("SELECT * FROM bookings WHERE customer_id = ? ORDER BY created_at DESC",
                          conn, params=(st.session_state.user[0],))
    conn.close()
    if not bookings.empty:
        st.dataframe(bookings)
    else:
        st.info("No bookings found")

# ==================== LOGIN ====================

def login_page():
    st.markdown("<div class='header-gradient'><h1>🔑 Login</h1></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        try:
            admin_user = st.secrets["admin"]["username"]
        except:
            admin_user = "admin"
        
        st.markdown(f"""
        <div class='credentials-box'>
            <strong>📝 Test Credentials:</strong><br>
            👑 Admin: <code>{admin_user}</code> / <code>admin123</code><br>
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

            user = authenticate_user(username, password)

            if user is None:
                st.error("❌ Invalid username or password")
                return

            if user[5] == user_type:
                st.session_state.user = user
                st.success("✅ Login successful!")
                st.session_state.page = "Dashboard"
                st.rerun()
            else:
                st.error(f"❌ User type mismatch. User is '{user[5]}', you selected '{user_type}'")

# ==================== MAIN ====================

def main():
    # Initialize database
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
        if st.session_state.page == "Dashboard":
            admin_dashboard()
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
        st.markdown("<div class='header-gradient'><h1>🚗 Driver Dashboard</h1></div>", unsafe_allow_html=True)
        st.info("Driver features coming soon!")

if __name__ == "__main__":
    main()
