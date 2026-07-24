import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
from datetime import datetime
import hashlib

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="SwiftGo HyperLocal Platform",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern Blue and White Professional Theme Styling
st.markdown("""
<style>
    .main {
        background-color: #F8FAFC;
        color: #1E293B;
    }
    .sidebar .sidebar-content {
        background-color: #FFFFFF;
    }
    h1, h2, h3 {
        color: #0F172A;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    .stButton>button {
        background-color: #2563EB;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        border: none;
        font-weight: 600;
        width: 100%;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #1D4ED8;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
    }
    .card {
        background: #FFFFFF;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        margin-bottom: 20px;
        border: 1px solid #E2E8F0;
    }
    .metric-card {
        background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%);
        border: 1px solid #BFDBFE;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        color: #1E40AF;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# DATABASE SETUP & INITIALIZATION
# -----------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect('hyperlocal.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            phone TEXT,
            status TEXT DEFAULT 'approved',
            wallet REAL DEFAULT 200.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Bookings / Services Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            driver_id INTEGER,
            category TEXT NOT NULL,
            subcategory TEXT NOT NULL,
            pickup TEXT NOT NULL,
            dropoff TEXT NOT NULL,
            fare REAL NOT NULL,
            status TEXT DEFAULT 'Requested',
            rating INTEGER DEFAULT 0,
            review TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(customer_id) REFERENCES users(id),
            FOREIGN KEY(driver_id) REFERENCES users(id)
        )
    ''')
    
    # Notifications Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT NOT NULL,
            read_status INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # Transactions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # Create Default Admin, Driver, and Customer if empty
    cursor.execute("SELECT * FROM users WHERE email = 'admin@hyperlocal.com'")
    if not cursor.fetchone():
        admin_pw = hashlib.sha256('admin123'.encode()).hexdigest()
        cursor.execute("INSERT INTO users (name, email, password, role, phone, status, wallet) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       ('System Admin', 'admin@hyperlocal.com', admin_pw, 'admin', '9999999999', 'approved', 5000.0))
        
        driver_pw = hashlib.sha256('driver123'.encode()).hexdigest()
        cursor.execute("INSERT INTO users (name, email, password, role, phone, status, wallet) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       ('John Driver', 'driver@hyperlocal.com', driver_pw, 'driver', '8888888888', 'approved', 450.0))
        
        cust_pw = hashlib.sha256('cust123'.encode()).hexdigest()
        cursor.execute("INSERT INTO users (name, email, password, role, phone, status, wallet) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       ('Alice Customer', 'customer@hyperlocal.com', cust_pw, 'customer', '7777777777', 'approved', 300.0))
        
    conn.commit()
    conn.close()

init_db()

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def run_query(query, params=(), fetch=False):
    conn = sqlite3.connect('hyperlocal.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(query, params)
    if fetch:
        result = cursor.fetchall()
        conn.close()
        return result
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

if 'user' not in st.session_state:
    st.session_state.user = None

# -----------------------------------------------------------------------------
# AUTHENTICATION PAGE
# -----------------------------------------------------------------------------
def auth_page():
    st.markdown("<h1 style='text-align: center; color: #2563EB;'>🚀 SwiftGo HyperLocal Platform</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748B;'>Rides, Deliveries, and Local Home Services at your Doorstep</p><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2, tab3 = st.tabs(["🔑 Login", "📝 Customer Register", "🚗 Driver Register"])
        
        with tab1:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader("Account Login")
            email = st.text_input("Email Address", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login to Account"):
                hashed = hash_password(password)
                users = run_query("SELECT id, name, email, role, wallet, status, phone FROM users WHERE email = ? AND password = ?", (email, hashed), fetch=True)
                if users:
                    user = users[0]
                    if user[3] == 'driver' and user[5] != 'approved':
                        st.error("Your driver account is pending admin approval.")
                    else:
                        st.session_state.user = {
                            "id": user[0], "name": user[1], "email": user[2],
                            "role": user[3], "wallet": user[4], "status": user[5], "phone": user[6]
                        }
                        st.success(f"Welcome back, {user[1]}!")
                        st.rerun()
                else:
                    st.error("Invalid email or password.")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with tab2:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader("Customer Sign Up")
            c_name = st.text_input("Full Name", key="c_name")
            c_email = st.text_input("Email", key="c_email")
            c_phone = st.text_input("Phone Number", key="c_phone")
            c_pass = st.text_input("Password", type="password", key="c_pass")
            if st.button("Register Customer"):
                if c_name and c_email and c_pass:
                    try:
                        hashed = hash_password(c_pass)
                        run_query("INSERT INTO users (name, email, password, role, phone, status, wallet) VALUES (?, ?, ?, 'customer', ?, 'approved', 200.0)",
                                  (c_name, c_email, hashed, c_phone))
                        st.success("Registration successful! Please login.")
                    except sqlite3.IntegrityError:
                        st.error("Email already registered.")
                else:
                    st.warning("Please fill all required fields.")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with tab3:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader("Driver Sign Up")
            d_name = st.text_input("Full Name", key="d_name")
            d_email = st.text_input("Email", key="d_email")
            d_phone = st.text_input("Phone Number", key="d_phone")
            d_pass = st.text_input("Password", type="password", key="d_pass")
            if st.button("Register Driver"):
                if d_name and d_email and d_pass:
                    try:
                        hashed = hash_password(d_pass)
                        run_query("INSERT INTO users (name, email, password, role, phone, status, wallet) VALUES (?, ?, ?, 'driver', ?, 'pending', 0.0)",
                                  (d_name, d_email, hashed, d_phone))
                        st.success("Registration submitted! Awaiting admin approval.")
                    except sqlite3.IntegrityError:
                        st.error("Email already registered.")
                else:
                    st.warning("Please fill all required fields.")
            st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SIDEBAR NAVIGATION
# -----------------------------------------------------------------------------
def render_sidebar():
    user = st.session_state.user
    st.sidebar.markdown(f"### 👤 Welcome, **{user['name']}**")
    st.sidebar.markdown(f"**Role:** `{user['role'].upper()}`")
    if user['role'] != 'admin':
        st.sidebar.markdown(f"💰 **Wallet:** ₹{user['wallet']:.2f}")
    
    st.sidebar.markdown("---")
    
    if user['role'] == 'customer':
        menu = st.sidebar.radio("Navigation", [
            "🚗 Book Ride", 
            "📦 Parcel Delivery", 
            "🔧 Local Services", 
            "📋 My Bookings", 
            "💳 Wallet & Topup", 
            "🔔 Notifications", 
            "⭐ Ratings & Reviews"
        ])
    elif user['role'] == 'driver':
        menu = st.sidebar.radio("Navigation", [
            "🚖 Available Requests", 
            "🗺️ Active Ride & Simulation", 
            "💵 Earnings & Wallet", 
            "📋 Job History"
        ])
    else: # admin
        menu = st.sidebar.radio("Navigation", [
            "📊 Admin Dashboard", 
            "👥 Approve Drivers", 
            "👤 Manage Users", 
            "📋 All Bookings", 
            "📈 Analytics & Reports"
        ])
        
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.user = None
        st.rerun()
        
    return menu

# -----------------------------------------------------------------------------
# CUSTOMER MODULES
# -----------------------------------------------------------------------------
def customer_book_ride():
    st.header("🚗 Book a Ride (Bike, Auto, Cab)")
    st.markdown("Get instant fares and book verified transport.")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        ride_type = st.selectbox("Select Vehicle", ["Bike (₹10/km)", "Auto (₹15/km)", "Cab (₹25/km)"])
        pickup = st.text_input("Pickup Location", "Central Railway Station")
        dropoff = st.text_input("Dropoff Location", "Tech Park, Sector 4")
        distance = st.slider("Estimated Distance (km)", 1, 40, 6)
        
        rate = 10 if "Bike" in ride_type else (15 if "Auto" in ride_type else 25)
        base = 30 if "Bike" in ride_type else (50 if "Auto" in ride_type else 100)
        total_fare = base + (distance * rate)
        
        st.info(f"Calculated Fare: **₹{total_fare}** (Base: ₹{base} + {distance}km @ ₹{rate}/km)")
        
        if st.button("Confirm Ride Booking"):
            user = st.session_state.user
            if user['wallet'] < total_fare:
                st.error("Insufficient wallet balance. Please top up in the Wallet section.")
            else:
                new_wallet = user['wallet'] - total_fare
                run_query("UPDATE users SET wallet = ? WHERE id = ?", (new_wallet, user['id']))
                st.session_state.user['wallet'] = new_wallet
                
                run_query("INSERT INTO bookings (customer_id, category, subcategory, pickup, dropoff, fare, status) VALUES (?, 'Ride', ?, ?, ?, ?, 'Requested')",
                          (user['id'], ride_type.split()[0], pickup, dropoff, total_fare))
                run_query("INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, 'Debit', ?)",
                          (user['id'], total_fare, f"Ride booking: {ride_type}"))
                run_query("INSERT INTO notifications (user_id, message) VALUES (?, ?)",
                          (user['id'], f"Ride booked successfully for {ride_type}. Searching for nearby drivers."))
                st.success("Ride successfully requested! Check 'My Bookings' for status updates.")
                
    with col2:
        st.subheader("Route Map Preview")
        m = folium.Map(location=[17.3850, 78.4867], zoom_start=13)
        folium.Marker([17.3850, 78.4867], popup="Pickup", icon=folium.Icon(color="green", icon="play")).add_to(m)
        folium.Marker([17.4050, 78.5050], popup="Dropoff", icon=folium.Icon(color="red", icon="stop")).add_to(m)
        st_folium(m, width=500, height=350)

def customer_parcel_delivery():
    st.header("📦 Parcel Delivery")
    st.markdown("Send documents, food, and packages securely across the city.")
    
    col1, col2 = st.columns(2)
    with col1:
        p_type = st.selectbox("Parcel Category", ["Documents", "Electronics", "Groceries & Food", "Apparel & Gifts"])
        weight = st.number_input("Package Weight (kg)", min_value=0.5, max_value=25.0, value=2.0)
        sender = st.text_input("Pickup Address", "Sender Home / Office")
        receiver = st.text_input("Recipient Address", "Receiver Destination")
        
        fare = 60 + (weight * 15)
        st.info(f"Estimated Delivery Charge: **₹{fare}**")
        
        if st.button("Schedule Parcel Delivery"):
            user = st.session_state.user
            if user['wallet'] < fare:
                st.error("Insufficient wallet balance.")
            else:
                new_wallet = user['wallet'] - fare
                run_query("UPDATE users SET wallet = ? WHERE id = ?", (new_wallet, user['id']))
                st.session_state.user['wallet'] = new_wallet
                
                run_query("INSERT INTO bookings (customer_id, category, subcategory, pickup, dropoff, fare, status) VALUES (?, 'Parcel', ?, ?, ?, ?, 'Requested')",
                          (user['id'], p_type, sender, receiver, fare))
                run_query("INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, 'Debit', ?)",
                          (user['id'], fare, f"Parcel Delivery: {p_type}"))
                st.success("Parcel pickup scheduled successfully!")
    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### Delivery Assurance")
        st.markdown("- Secure handling & live updates\n- Max weight limit: 25 kg\n- Instant delivery partner assignment\n- Instant proof of delivery")
        st.markdown("</div>", unsafe_allow_html=True)

def customer_local_services():
    st.header("🔧 Local Home & Repair Services")
    st.markdown("Hire expert professionals for instant repairs and home maintenance.")
    
    service = st.selectbox("Service Type", ["Electrician", "Plumber", "AC Repair", "Laptop Repair", "Mobile Repair"])
    issue_desc = st.text_area("Describe the issue / requirements")
    slot = st.text_input("Preferred Time Slot", "Today, 5:00 PM")
    
    fares = {"Electrician": 299, "Plumber": 299, "AC Repair": 499, "Laptop Repair": 399, "Mobile Repair": 349}
    fare = fares.get(service, 300)
    
    st.info(f"Standard Inspection & Service Charge: **₹{fare}**")
    
    if st.button("Book Professional"):
        user = st.session_state.user
        if user['wallet'] < fare:
            st.error("Insufficient wallet balance.")
        else:
            new_wallet = user['wallet'] - fare
            run_query("UPDATE users SET wallet = ? WHERE id = ?", (new_wallet, user['id']))
            st.session_state.user['wallet'] = new_wallet
            
            run_query("INSERT INTO bookings (customer_id, category, subcategory, pickup, dropoff, fare, status) VALUES (?, 'Local Service', ?, ?, 'Customer Location', ?, 'Requested')",
                      (user['id'], service, issue_desc, fare))
            run_query("INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, 'Debit', ?)",
                      (user['id'], fare, f"Local Service: {service}"))
            st.success(f"{service} professional successfully booked for {slot}!")

def customer_my_bookings():
    st.header("📋 My Bookings & History")
    user = st.session_state.user
    
    col1, col2 = st.columns(2)
    with col1:
        search = st.text_input("Search bookings by location/type", "")
    with col2:
        status_filter = st.selectbox("Filter Status", ["All", "Requested", "Accepted", "Ongoing", "Completed", "Cancelled"])
        
    query = "SELECT id, category, subcategory, pickup, dropoff, fare, status, created_at FROM bookings WHERE customer_id = ?"
    params = [user['id']]
    if status_filter != "All":
        query += " AND status = ?"
        params.append(status_filter)
        
    bookings = run_query(query, tuple(params), fetch=True)
    
    if bookings:
        for b in bookings:
            if search.lower() in b[1].lower() or search.lower() in b[2].lower() or search.lower() in b[3].lower():
                st.markdown(f"""
                <div class='card'>
                    <h4>Booking #{b[0]} - {b[1]} ({b[2]})</h4>
                    <p><b>Pickup:</b> {b[3]} | <b>Dropoff:</b> {b[4]}</p>
                    <p><b>Fare:</b> ₹{b[5]} | <b>Status:</b> <code>{b[6]}</code> | <b>Date:</b> {b[7]}</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No matching bookings found.")

def customer_wallet():
    st.header("💳 Wallet & Top-up")
    user = st.session_state.user
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <h2>Available Balance</h2>
            <h1>₹{user['wallet']:.2f}</h1>
        </div>
        """, unsafe_allow_html=True)
        
        topup = st.number_input("Add Funds (₹)", min_value=100, max_value=10000, value=500, step=100)
        if st.button("Top Up Wallet Now"):
            new_wallet = user['wallet'] + topup
            run_query("UPDATE users SET wallet = ? WHERE id = ?", (new_wallet, user['id']))
            st.session_state.user['wallet'] = new_wallet
            run_query("INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, 'Credit', 'Wallet Top-up')",
                      (user['id'], topup))
            st.success(f"Successfully added ₹{topup} to wallet!")
            st.rerun()
            
    with col2:
        st.subheader("Transaction History")
        txns = run_query("SELECT amount, type, description, created_at FROM transactions WHERE user_id = ? ORDER BY id DESC", (user['id'],), fetch=True)
        if txns:
            for t in txns:
                color = "green" if t[1] == 'Credit' else "red"
                st.markdown(f"<p><b>{t[3]}</b> - {t[2]}: <span style='color:{color};'><b>₹{t[0]} ({t[1]})</b></span></p>", unsafe_allow_html=True)
        else:
            st.info("No transactions recorded.")

def customer_notifications():
    st.header("🔔 Notifications")
    user = st.session_state.user
    notifs = run_query("SELECT message, created_at FROM notifications WHERE user_id = ? ORDER BY id DESC", (user['id'],), fetch=True)
    if notifs:
        for n in notifs:
            st.markdown(f"<div class='card'><p><b>{n[1]}</b></p><p>{n[0]}</p></div>", unsafe_allow_html=True)
    else:
        st.info("No notifications.")

def customer_ratings():
    st.header("⭐ Ratings & Reviews")
    user = st.session_state.user
    completed = run_query("SELECT id, category, subcategory, pickup, dropoff FROM bookings WHERE customer_id = ? AND status = 'Completed' AND rating = 0", (user['id'],), fetch=True)
    
    if completed:
        options = {f"Booking #{b[0]} - {b[1]} ({b[2]})": b[0] for b in completed}
        sel = st.selectbox("Select Completed Service to Review", list(options.keys()))
        b_id = options[sel]
        
        rating = st.slider("Rating (1-5 Stars)", 1, 5, 5)
        review = st.text_area("Write Feedback")
        if st.button("Submit Review"):
            run_query("UPDATE bookings SET rating = ?, review = ? WHERE id = ?", (rating, review, b_id))
            st.success("Thank you for your feedback!")
            st.rerun()
    else:
        st.info("No pending reviews for completed bookings.")

# -----------------------------------------------------------------------------
# DRIVER MODULES
# -----------------------------------------------------------------------------
def driver_dashboard():
    st.header("🚖 Driver Dashboard - Available Requests")
    user = st.session_state.user
    
    online = st.checkbox("🟢 Online Status (Ready to receive requests)", value=True)
    
    if online:
        reqs = run_query("SELECT b.id, u.name, b.category, b.subcategory, b.pickup, b.dropoff, b.fare FROM bookings b JOIN users u ON b.customer_id = u.id WHERE b.status = 'Requested'", fetch=True)
        if reqs:
            for r in reqs:
                st.markdown(f"""
                <div class='card'>
                    <h3>Booking #{r[0]} | {r[2]} ({r[3]})</h3>
                    <p><b>Customer:</b> {r[1]} | <b>Fare Offer:</b> ₹{r[6]}</p>
                    <p><b>Pickup:</b> {r[4]} <br><b>Dropoff:</b> {r[5]}</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Accept Request #{r[0]}", key=f"acc_{r[0]}"):
                    run_query("UPDATE bookings SET status = 'Accepted', driver_id = ? WHERE id = ?", (user['id'], r[0]))
                    run_query("INSERT INTO notifications (user_id, message) VALUES (?, ?)", (r[0], f"Driver accepted booking #{r[0]}. En route to pickup."))
                    st.success(f"Accepted booking #{r[0]}!")
                    st.rerun()
        else:
            st.info("No pending requests available right now.")
    else:
        st.warning("You are offline. Turn on your online status to receive requests.")

def driver_active_rides():
    st.header("🗺️ Active Ride & Simulation")
    user = st.session_state.user
    active = run_query("SELECT b.id, u.name, u.phone, b.category, b.pickup, b.dropoff, b.fare, b.status FROM bookings b JOIN users u ON b.customer_id = u.id WHERE b.driver_id = ? AND b.status IN ('Accepted', 'Ongoing')", (user['id'],), fetch=True)
    
    if active:
        for a in active:
            st.markdown(f"""
            <div class='card'>
                <h3>Active Booking #{a[0]} ({a[3]})</h3>
                <p><b>Customer:</b> {a[1]} ({a[2]}) | <b>Status:</b> <code>{a[7]}</code></p>
                <p><b>Pickup:</b> {a[4]} &rarr; <b>Dropoff:</b> {a[5]}</p>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if a[7] == 'Accepted':
                    if st.button("Start Trip / Ongoing", key=f"start_{a[0]}"):
                        run_query("UPDATE bookings SET status = 'Ongoing' WHERE id = ?", (a[0],))
                        st.success("Trip started!")
                        st.rerun()
                elif a[7] == 'Ongoing':
                    if st.button("Complete Ride / Service", key=f"comp_{a[0]}"):
                        run_query("UPDATE bookings SET status = 'Completed' WHERE id = ?", (a[0],))
                        earnings = a[6] * 0.85
                        new_wallet = user['wallet'] + earnings
                        run_query("UPDATE users SET wallet = ? WHERE id = ?", (new_wallet, user['id']))
                        st.session_state.user['wallet'] = new_wallet
                        run_query("INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, 'Credit', ?)",
                                  (user['id'], earnings, f"Earnings from booking #{a[0]}"))
                        st.success(f"Booking completed! Earned ₹{earnings:.2f} (85% commission share).")
                        st.rerun()
            with col2:
                st.subheader("Live Simulation Map")
                m = folium.Map(location=[17.3850, 78.4867], zoom_start=14)
                folium.Marker([17.3850, 78.4867], popup="Driver Current Location", icon=folium.Icon(color="blue", icon="car")).add_to(m)
                st_folium(m, width=400, height=250)
    else:
        st.info("No active rides or jobs assigned.")

def driver_earnings():
    st.header("💵 Driver Earnings & Wallet")
    user = st.session_state.user
    st.markdown(f"""
    <div class='metric-card'>
        <h2>Total Driver Earnings Wallet</h2>
        <h1>₹{user['wallet']:.2f}</h1>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader("Earnings Breakdown")
    txns = run_query("SELECT amount, type, description, created_at FROM transactions WHERE user_id = ? ORDER BY id DESC", (user['id'],), fetch=True)
    if txns:
        for t in txns:
            st.markdown(f"<p><b>{t[3]}</b> - {t[2]}: <span style='color:green;'><b>₹{t[0]}</b></span></p>", unsafe_allow_html=True)
    else:
        st.info("No earnings recorded yet.")

def driver_history():
    st.header("📋 Completed Jobs History")
    user = st.session_state.user
    history = run_query("SELECT id, category, subcategory, pickup, dropoff, fare, created_at FROM bookings WHERE driver_id = ? AND status = 'Completed'", (user['id'],), fetch=True)
    if history:
        for h in history:
            st.markdown(f"""
            <div class='card'>
                <h4>Booking #{h[0]} - {h[1]} ({h[2]})</h4>
                <p><b>Pickup:</b> {h[3]} | <b>Dropoff:</b> {h[4]}</p>
                <p><b>Fare:</b> ₹{h[5]} | <b>Completed:</b> {h[6]}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No completed jobs in history.")

# -----------------------------------------------------------------------------
# ADMIN MODULES
# -----------------------------------------------------------------------------
def admin_dashboard():
    st.header("📊 Admin Revenue & System Dashboard")
    
    users_cnt = run_query("SELECT COUNT(*) FROM users", fetch=True)[0][0]
    bookings_cnt = run_query("SELECT COUNT(*) FROM bookings", fetch=True)[0][0]
    revenue = run_query("SELECT SUM(fare) FROM bookings WHERE status = 'Completed'", fetch=True)[0][0] or 0.0
    pending_cnt = run_query("SELECT COUNT(*) FROM users WHERE role = 'driver' AND status = 'pending'", fetch=True)[0][0]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Users", users_cnt)
    with col2:
        st.metric("Total Bookings", bookings_cnt)
    with col3:
        st.metric("Gross Revenue", f"₹{revenue:.2f}")
    with col4:
        st.metric("Pending Drivers", pending_cnt)
        
    st.markdown("---")
    st.subheader("Revenue by Service Category")
    df = pd.read_sql("SELECT category, fare, status FROM bookings", sqlite3.connect('hyperlocal.db'))
    if not df.empty:
        fig = px.bar(df, x='category', y='fare', color='status', title="Revenue Breakdown", barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No analytics data available yet.")

def admin_approve_drivers():
    st.header("👥 Driver Approval Management")
    pending = run_query("SELECT id, name, email, phone, created_at FROM users WHERE role = 'driver' AND status = 'pending'", fetch=True)
    
    if pending:
        for d in pending:
            st.markdown(f"""
            <div class='card'>
                <h4>{d[1]} ({d[2]})</h4>
                <p><b>Phone:</b> {d[3]} | <b>Requested:</b> {d[4]}</p>
            </div>
            """, unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Approve #{d[0]}", key=f"approve_{d[0]}"):
                    run_query("UPDATE users SET status = 'approved' WHERE id = ?", (d[0],))
                    run_query("INSERT INTO notifications (user_id, message) VALUES (?, ?)", (d[0], "Your driver account is now approved!"))
                    st.success(f"Driver {d[1]} approved!")
                    st.rerun()
            with col2:
                if st.button(f"Reject #{d[0]}", key=f"reject_{d[0]}"):
                    run_query("DELETE FROM users WHERE id = ?", (d[0],))
                    st.warning("Driver application rejected.")
                    st.rerun()
    else:
        st.success("No pending driver approvals.")

def admin_manage_users():
    st.header("👤 Manage All Users")
    users = run_query("SELECT id, name, email, role, status, wallet, phone FROM users", fetch=True)
    df_u = pd.DataFrame(users, columns=["ID", "Name", "Email", "Role", "Status", "Wallet", "Phone"])
    st.dataframe(df_u, use_container_width=True)

def admin_all_bookings():
    st.header("📋 All System Bookings & Reports")
    bookings = run_query("SELECT b.id, u.name, b.category, b.subcategory, b.pickup, b.dropoff, b.fare, b.status, b.created_at FROM bookings b JOIN users u ON b.customer_id = u.id", fetch=True)
    if bookings:
        df_b = pd.DataFrame(bookings, columns=["ID", "Customer", "Category", "Subcategory", "Pickup", "Dropoff", "Fare", "Status", "Date"])
        
        search = st.text_input("Search Bookings", "")
        if search:
            df_b = df_b[df_b.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
            
        st.dataframe(df_b, use_container_width=True)
        
        csv = df_b.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Bookings CSV", data=csv, file_name="hyperlocal_bookings_report.csv", mime="text/csv")
    else:
        st.info("No bookings recorded.")

def admin_analytics():
    st.header("📈 Advanced Analytics Reports")
    df = pd.read_sql("SELECT * FROM bookings", sqlite3.connect('hyperlocal.db'))
    if not df.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.pie(df, names='category', title="Bookings Share by Category")
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            fig2 = px.histogram(df, x='fare', title="Fare Distribution Histogram")
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Not enough data for analytics.")

# -----------------------------------------------------------------------------
# MAIN DISPATCHER
# -----------------------------------------------------------------------------
def main():
    if st.session_state.user is None:
        auth_page()
    else:
        menu = render_sidebar()
        user = st.session_state.user
        
        if user['role'] == 'customer':
            if menu == "🚗 Book Ride":
                customer_book_ride()
            elif menu == "📦 Parcel Delivery":
                customer_parcel_delivery()
            elif menu == "🔧 Local Services":
                customer_local_services()
            elif menu == "📋 My Bookings":
                customer_my_bookings()
            elif menu == "💳 Wallet & Topup":
                customer_wallet()
            elif menu == "🔔 Notifications":
                customer_notifications()
            elif menu == "⭐ Ratings & Reviews":
                customer_ratings()
                
        elif user['role'] == 'driver':
            if menu == "🚖 Available Requests":
                driver_dashboard()
            elif menu == "🗺️ Active Ride & Simulation":
                driver_active_rides()
            elif menu == "💵 Earnings & Wallet":
                driver_earnings()
            elif menu == "📋 Job History":
                driver_history()
                
        elif user['role'] == 'admin':
            if menu == "📊 Admin Dashboard":
                admin_dashboard()
            elif menu == "👥 Approve Drivers":
                admin_approve_drivers()
            elif menu == "👤 Manage Users":
                admin_manage_users()
            elif menu == "📋 All Bookings":
                admin_all_bookings()
            elif menu == "📈 Analytics & Reports":
                admin_analytics()

if __name__ == '__main__':
    main()
