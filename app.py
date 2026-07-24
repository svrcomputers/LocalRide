"""
HyperLocal Ride Booking - GUARANTEED WORKING VERSION
"""

import streamlit as st
import sqlite3
import hashlib

# ==================== DATABASE SETUP ====================

def init_db():
    """Initialize database with USERS - GUARANTEED"""
    try:
        # Connect
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
            status TEXT DEFAULT 'approved'
        )''')
        
        # IMPORTANT: Delete all first to avoid conflicts
        c.execute("DELETE FROM users")
        
        # Insert users one by one
        admin_pass = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, full_name, phone, user_type, status) VALUES (?, ?, ?, ?, ?, ?)",
                  ('admin', admin_pass, 'System Admin', '9999999999', 'admin', 'approved'))
        
        customer_pass = hashlib.sha256('customer123'.encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, full_name, phone, user_type, status) VALUES (?, ?, ?, ?, ?, ?)",
                  ('customer', customer_pass, 'Test Customer', '9876543210', 'customer', 'approved'))
        
        # IMPORTANT: Commit the changes
        conn.commit()
        
        # Verify users exist
        c.execute("SELECT username, user_type FROM users")
        users = c.fetchall()
        print("✅ USERS IN DATABASE:", users)
        
        # Close connection
        conn.close()
        return True
        
    except Exception as e:
        print("❌ ERROR:", e)
        return False

# ==================== AUTHENTICATION ====================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_user(username, password):
    """Check if user exists"""
    try:
        conn = sqlite3.connect('hyperlocal.db')
        c = conn.cursor()
        hashed = hash_password(password)
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed))
        user = c.fetchone()
        conn.close()
        return user
    except:
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
            
            if st.button("Dashboard"):
                st.session_state.page = "Dashboard"
                st.rerun()
            if st.button("Logout"):
                for key in ['user', 'page']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

# ==================== ADMIN ====================

def admin_dashboard():
    st.markdown("<div class='header-gradient'><h1>📊 Admin Dashboard</h1></div>", unsafe_allow_html=True)
    
    conn = sqlite3.connect('hyperlocal.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    
    st.write("### Users in Database")
    for user in users:
        st.write(f"ID: {user[0]}, Username: {user[1]}, Type: {user[5]}, Status: {user[6]}")

# ==================== CUSTOMER ====================

def customer_dashboard():
    st.markdown("<div class='header-gradient'><h1>🏠 Customer Dashboard</h1></div>", unsafe_allow_html=True)
    st.info("Welcome to your dashboard!")

# ==================== LOGIN ====================

def login_page():
    st.markdown("<div class='header-gradient'><h1>🔑 Login</h1></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class='credentials-box'>
            <strong>📝 Use these credentials:</strong><br>
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
            
            # Try to login
            user = login_user(username, password)
            
            if user is None:
                st.error("❌ Invalid username or password")
                return
            
            # Check if the role matches
            if user[5] == user_type:
                st.session_state.user = user
                st.success("✅ Login successful!")
                st.session_state.page = "Dashboard"
                st.rerun()
            else:
                st.error(f"❌ Role mismatch. User is '{user[5]}', you selected '{user_type}'")

# ==================== MAIN ====================

def main():
    # Initialize database - THIS MUST RUN FIRST
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
    if st.session_state.user[5] == 'admin':
        admin_dashboard()
    else:
        customer_dashboard()

if __name__ == "__main__":
    main()
