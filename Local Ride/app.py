"""
Hyper Local Ride Booking Application
A complete ride booking, parcel delivery, and local services platform.
Built with Streamlit, SQLite, and Folium.
"""

import streamlit as st
import sqlite3
import hashlib
import json
import time
import random
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import io
import base64

# ==================== DATABASE SETUP ====================

def init_db():
    """Initialize SQLite database with all required tables"""
    conn = sqlite3.connect('hyperlocal.db')
    c = conn.cursor()
    
    # Users table (customers and drivers)
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
    
    # Driver specific details
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
        current_location TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Bookings table
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
        review TEXT,
        FOREIGN KEY (customer_id) REFERENCES users (id),
        FOREIGN KEY (driver_id) REFERENCES users (id)
    )''')
    
    # Parcel deliveries
    c.execute('''CREATE TABLE IF NOT EXISTS parcels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        parcel_type TEXT NOT NULL,
        weight REAL NOT NULL,
        description TEXT,
        receiver_name TEXT NOT NULL,
        receiver_phone TEXT NOT NULL,
        FOREIGN KEY (booking_id) REFERENCES bookings (id)
    )''')
    
    # Local services
    c.execute('''CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider_id INTEGER NOT NULL,
        service_type TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        rating REAL DEFAULT 0.0,
        is_available BOOLEAN DEFAULT 1,
        FOREIGN KEY (provider_id) REFERENCES users (id)
    )''')
    
    # Service bookings
    c.execute('''CREATE TABLE IF NOT EXISTS service_bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_id INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        booking_date DATE NOT NULL,
        booking_time TIME NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (service_id) REFERENCES services (id),
        FOREIGN KEY (customer_id) REFERENCES users (id)
    )''')
    
    # Wallet transactions
    c.execute('''CREATE TABLE IF NOT EXISTS wallet (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        transaction_type TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Notifications
    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        is_read BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Reviews
    c.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        reviewer_id INTEGER NOT NULL,
        reviewee_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (booking_id) REFERENCES bookings (id),
        FOREIGN KEY (reviewer_id) REFERENCES users (id),
        FOREIGN KEY (reviewee_id) REFERENCES users (id)
    )''')
    
    # Admin user (default)
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        admin_pass = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, full_name, phone, user_type, status) VALUES (?, ?, ?, ?, ?, ?)",
                 ('admin', admin_pass, 'System Admin', '9999999999', 'admin', 'approved'))
    
    conn.commit()
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

def register_user(username, password, full_name, phone, email, user_type):
    conn = sqlite3.connect('hyperlocal.db')
    c = conn.cursor()
    try:
        hashed = hash_password(password)
        c.execute("INSERT INTO users (username, password, full_name, phone, email, user_type, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (username, hashed, full_name, phone, email, user_type, 'pending' if user_type == 'driver' else 'approved'))
        user_id = c.lastrowid
        
        if user_type == 'driver':
            c.execute("INSERT INTO drivers (user_id, vehicle_type, vehicle_number, license_number) VALUES (?, ?, ?, ?)",
                     (user_id, 'bike', 'TN01AB1234', 'DL1234567890'))
        
        conn.commit()
        return True, user_id
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    finally:
        conn.close()

# ==================== UI COMPONENTS ====================

def set_page_config():
    """Configure Streamlit page"""
    st.set_page_config(
        page_title="HyperLocal Ride Booking",
        page_icon="🚗",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for blue and white theme
    st.markdown("""
    <style>
        /* Main theme */
        .main {
            background-color: #ffffff;
        }
        .stButton > button {
            background-color: #1a73e8;
            color: white;
            border-radius: 25px;
            padding: 10px 25px;
            border: none;
            font-weight: 600;
            transition: all 0.3s ease;
            width: 100%;
        }
        .stButton > button:hover {
            background-color: #1557b0;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(26, 115, 232, 0.3);
        }
        .sidebar .sidebar-content {
            background: linear-gradient(180deg, #1a73e8 0%, #0d47a1 100%);
            color: white;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            border-left: 4px solid #1a73e8;
            transition: all 0.3s ease;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(26, 115, 232, 0.15);
        }
        .metric-card {
            background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);
            padding: 20px;
            border-radius: 15px;
            color: white;
            text-align: center;
        }
        .status-badge {
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .status-pending { background: #fff3cd; color: #856404; }
        .status-approved { background: #d4edda; color: #155724; }
        .status-rejected { background: #f8d7da; color: #721c24; }
        .status-completed { background: #cce5ff; color: #004085; }
        .status-in-progress { background: #d1ecf1; color: #0c5460; }
        .fare-badge {
            background: #1a73e8;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
        }
        .stTextInput > div > div > input {
            border-radius: 10px;
            border: 2px solid #e8f0fe;
            padding: 10px;
        }
        .stSelectbox > div > div > select {
            border-radius: 10px;
            border: 2px solid #e8f0fe;
            padding: 10px;
        }
        h1, h2, h3 {
            color: #1a73e8;
        }
        .header-gradient {
            background: linear-gradient(135deg, #1a73e8, #0d47a1);
            padding: 20px;
            border-radius: 15px;
            color: white;
            margin-bottom: 30px;
        }
        .notification-badge {
            background: #ff4444;
            color: white;
            border-radius: 50%;
            padding: 2px 8px;
            font-size: 12px;
            position: absolute;
            top: -8px;
            right: -8px;
        }
    </style>
    """, unsafe_allow_html=True)

def show_sidebar():
    """Render sidebar with navigation"""
    with st.sidebar:
        st.image("https://via.placeholder.com/150x80/1a73e8/ffffff?text=HyperLocal", use_column_width=True)
        st.markdown("---")
        
        if 'user' in st.session_state:
            st.markdown(f"### 👋 Welcome, {st.session_state.user[3]}")
            st.markdown(f"**Role:** {st.session_state.user[5].title()}")
            st.markdown("---")
            
            # Navigation based on user type
            if st.session_state.user[5] == 'admin':
                menu = ["Dashboard", "Users", "Drivers", "Bookings", "Services", "Reports"]
                icon_map = ["📊", "👥", "🚗", "📋", "🔧", "📈"]
            elif st.session_state.user[5] == 'driver':
                menu = ["Dashboard", "My Rides", "Earnings", "Availability", "Profile"]
                icon_map = ["📊", "🚗", "💰", "🔄", "👤"]
            else:  # customer
                menu = ["Dashboard", "Book Ride", "Parcel Delivery", "Local Services", "My Bookings", "Wallet", "Profile"]
                icon_map = ["📊", "🚗", "📦", "🔧", "📋", "💰", "👤"]
            
            for i, item in enumerate(menu):
                if st.button(f"{icon_map[i]} {item}", key=f"nav_{item}"):
                    st.session_state.page = item
                    st.rerun()
            
            st.markdown("---")
            if st.button("🚪 Logout", key="logout"):
                for key in ['user', 'page']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        else:
            st.markdown("### Welcome!")
            st.markdown("Please login or register to continue.")
            if st.button("🔑 Login", key="login_btn"):
                st.session_state.page = "Login"
                st.rerun()
            if st.button("📝 Register", key="register_btn"):
                st.session_state.page = "Register"
                st.rerun()

# ==================== ADMIN FUNCTIONS ====================

def admin_dashboard():
    """Admin dashboard with analytics"""
    st.markdown("<div class='header-gradient'><h1>📊 Admin Dashboard</h1></div>", unsafe_allow_html=True)
    
    conn = sqlite3.connect('hyperlocal.db')
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_users = pd.read_sql("SELECT COUNT(*) as count FROM users WHERE user_type != 'admin'", conn)['count'][0]
        st.markdown(f"""
        <div class='metric-card'>
            <h3>👥 Total Users</h3>
            <h2>{total_users}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_drivers = pd.read_sql("SELECT COUNT(*) as count FROM users WHERE user_type = 'driver'", conn)['count'][0]
        st.markdown(f"""
        <div class='metric-card'>
            <h3>🚗 Total Drivers</h3>
            <h2>{total_drivers}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        total_bookings = pd.read_sql("SELECT COUNT(*) as count FROM bookings", conn)['count'][0]
        st.markdown(f"""
        <div class='metric-card'>
            <h3>📋 Total Bookings</h3>
            <h2>{total_bookings}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        revenue = pd.read_sql("SELECT SUM(fare) as total FROM bookings WHERE status = 'completed'", conn)['total'][0] or 0
        st.markdown(f"""
        <div class='metric-card'>
            <h3>💰 Revenue</h3>
            <h2>₹{revenue:,.0f}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Bookings Trend")
        bookings_df = pd.read_sql("""
            SELECT DATE(created_at) as date, COUNT(*) as count 
            FROM bookings 
            WHERE created_at >= DATE('now', '-7 days')
            GROUP BY DATE(created_at)
        """, conn)
        if not bookings_df.empty:
            fig = px.line(bookings_df, x='date', y='count', title="Last 7 Days")
            fig.update_layout(plot_bgcolor='white')
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📊 Service Distribution")
        service_df = pd.read_sql("""
            SELECT service_type, COUNT(*) as count 
            FROM bookings 
            GROUP BY service_type
        """, conn)
        if not service_df.empty:
            fig = px.pie(service_df, values='count', names='service_type', title="Bookings by Service")
            st.plotly_chart(fig, use_container_width=True)
    
    # Recent bookings
    st.subheader("🔄 Recent Bookings")
    recent = pd.read_sql("""
        SELECT b.*, u.full_name as customer_name 
        FROM bookings b 
        JOIN users u ON b.customer_id = u.id 
        ORDER BY b.created_at DESC 
        LIMIT 10
    """, conn)
    if not recent.empty:
        st.dataframe(recent[['id', 'customer_name', 'service_type', 'fare', 'status', 'created_at']], use_container_width=True)
    
    conn.close()

def admin_users():
    """Manage users"""
    st.header("👥 User Management")
    
    conn = sqlite3.connect('hyperlocal.db')
    users = pd.read_sql("SELECT id, username, full_name, phone, email, user_type, status, created_at FROM users WHERE user_type != 'admin'", conn)
    conn.close()
    
    if not users.empty:
        st.dataframe(users, use_container_width=True)
        
        # User actions
        col1, col2 = st.columns(2)
        with col1:
            user_id = st.selectbox("Select User ID", users['id'].tolist())
            action = st.selectbox("Action", ["Approve", "Suspend", "Delete"])
            if st.button("Execute Action"):
                conn = sqlite3.connect('hyperlocal.db')
                c = conn.cursor()
                if action == "Approve":
                    c.execute("UPDATE users SET status = 'approved' WHERE id = ?", (user_id,))
                elif action == "Suspend":
                    c.execute("UPDATE users SET status = 'suspended' WHERE id = ?", (user_id,))
                elif action == "Delete":
                    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
                conn.commit()
                conn.close()
                st.success(f"User {action}d successfully!")
                st.rerun()
    else:
        st.info("No users found")

def admin_drivers():
    """Approve and manage drivers"""
    st.header("🚗 Driver Management")
    
    conn = sqlite3.connect('hyperlocal.db')
    drivers = pd.read_sql("""
        SELECT u.id, u.username, u.full_name, u.phone, u.status, 
               d.vehicle_type, d.vehicle_number, d.rating, d.total_rides, d.earnings
        FROM users u 
        JOIN drivers d ON u.id = d.user_id 
        WHERE u.user_type = 'driver'
    """, conn)
    conn.close()
    
    if not drivers.empty:
        st.dataframe(drivers, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            driver_id = st.selectbox("Select Driver ID", drivers['id'].tolist())
            new_status = st.selectbox("Change Status", ["pending", "approved", "suspended"])
            if st.button("Update Status"):
                conn = sqlite3.connect('hyperlocal.db')
                c = conn.cursor()
                c.execute("UPDATE users SET status = ? WHERE id = ?", (new_status, driver_id))
                conn.commit()
                conn.close()
                st.success("Driver status updated!")
                st.rerun()
    else:
        st.info("No drivers registered yet")

def admin_bookings():
    """View all bookings"""
    st.header("📋 All Bookings")
    
    conn = sqlite3.connect('hyperlocal.db')
    bookings = pd.read_sql("""
        SELECT b.*, u.full_name as customer_name, d.full_name as driver_name 
        FROM bookings b 
        JOIN users u ON b.customer_id = u.id 
        LEFT JOIN users d ON b.driver_id = d.id 
        ORDER BY b.created_at DESC
    """, conn)
    conn.close()
    
    if not bookings.empty:
        st.dataframe(bookings, use_container_width=True)
    else:
        st.info("No bookings yet")

def admin_services():
    """Manage local services"""
    st.header("🔧 Local Services Management")
    
    conn = sqlite3.connect('hyperlocal.db')
    services = pd.read_sql("""
        SELECT s.*, u.full_name as provider_name 
        FROM services s 
        JOIN users u ON s.provider_id = u.id
    """, conn)
    conn.close()
    
    if not services.empty:
        st.dataframe(services, use_container_width=True)
    else:
        st.info("No services listed")

def admin_reports():
    """Generate reports and exports"""
    st.header("📈 Reports & Analytics")
    
    conn = sqlite3.connect('hyperlocal.db')
    
    # Revenue report
    st.subheader("Revenue Report")
    revenue_data = pd.read_sql("""
        SELECT DATE(created_at) as date, 
               COUNT(*) as bookings,
               SUM(fare) as revenue
        FROM bookings 
        WHERE status = 'completed'
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        LIMIT 30
    """, conn)
    
    if not revenue_data.empty:
        fig = px.bar(revenue_data, x='date', y=['bookings', 'revenue'], 
                     title="Daily Revenue & Bookings")
        st.plotly_chart(fig, use_container_width=True)
        
        # Export
        csv = revenue_data.to_csv(index=False)
        st.download_button(
            label="📥 Download Report (CSV)",
            data=csv,
            file_name=f"revenue_report_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No data available")
    
    conn.close()

# ==================== CUSTOMER FUNCTIONS ====================

def customer_dashboard():
    """Customer dashboard"""
    st.markdown("<div class='header-gradient'><h1>🏠 Customer Dashboard</h1></div>", unsafe_allow_html=True)
    
    conn = sqlite3.connect('hyperlocal.db')
    
    # Quick actions
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🚗 Book a Ride", use_container_width=True):
            st.session_state.page = "Book Ride"
            st.rerun()
    with col2:
        if st.button("📦 Parcel Delivery", use_container_width=True):
            st.session_state.page = "Parcel Delivery"
            st.rerun()
    with col3:
        if st.button("🔧 Local Services", use_container_width=True):
            st.session_state.page = "Local Services"
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
        for _, booking in recent.iterrows():
            status_class = f"status-{booking['status'].replace(' ', '-')}"
            st.markdown(f"""
            <div class='card'>
                <div style='display: flex; justify-content: space-between;'>
                    <div>
                        <strong>#{booking['id']}</strong> - {booking['service_type']}
                        <br>📍 {booking['pickup_location']}
                    </div>
                    <div>
                        <span class='status-badge {status_class}'>{booking['status'].upper()}</span>
                        <br>
                        <span class='fare-badge'>₹{booking['fare']:.0f}</span>
                    </div>
                </div>
                <small>{booking['created_at']}</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No bookings yet")
    
    conn.close()

def book_ride():
    """Book a ride (Bike, Auto, Cab)"""
    st.markdown("<div class='header-gradient'><h1>🚗 Book a Ride</h1></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        service_type = st.selectbox("Select Vehicle", ["Bike", "Auto", "Cab"])
        pickup = st.text_input("Pickup Location", "Your Location")
        dropoff = st.text_input("Dropoff Location", "Destination")
        
        # Fare calculator
        distance = random.uniform(2, 15)
        base_fares = {"Bike": 20, "Auto": 35, "Cab": 60}
        fare = base_fares[service_type] + (distance * 8)
        
        st.markdown(f"""
        <div class='card'>
            <h4>Fare Estimate</h4>
            <p>Distance: {distance:.1f} km</p>
            <p><strong>Estimated Fare: ₹{fare:.0f}</strong></p>
            <p><small>* Final fare may vary based on traffic and time</small></p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 📍 Map")
        m = folium.Map(location=[12.9716, 77.5946], zoom_start=12)
        folium.Marker([12.9716, 77.5946], popup="Your Location").add_to(m)
        st_folium(m, width=400, height=300)
    
    if st.button("🚗 Book Now", use_container_width=True):
        conn = sqlite3.connect('hyperlocal.db')
        c = conn.cursor()
        
        # Find available driver
        c.execute("""
            SELECT u.id FROM users u 
            JOIN drivers d ON u.id = d.user_id 
            WHERE u.status = 'approved' AND d.is_available = 1 
            AND d.vehicle_type = ? 
            LIMIT 1
        """, (service_type.lower(),))
        
        driver = c.fetchone()
        
        if driver:
            c.execute("""
                INSERT INTO bookings (customer_id, driver_id, service_type, pickup_location, 
                                     dropoff_location, fare, distance, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (st.session_state.user[0], driver[0], service_type, pickup, dropoff, fare, distance, 'in-progress'))
            
            booking_id = c.lastrowid
            
            # Update driver availability
            c.execute("UPDATE drivers SET is_available = 0 WHERE user_id = ?", (driver[0],))
            
            # Add notification
            c.execute("""
                INSERT INTO notifications (user_id, title, message)
                VALUES (?, ?, ?)
            """, (driver[0], "New Ride Request", f"New {service_type} booking from {pickup} to {dropoff}"))
            
            conn.commit()
            st.success(f"✅ Ride booked successfully! Booking ID: #{booking_id}")
            
            # Simulate ride status
            st.markdown("### 🚦 Live Ride Status")
            status_placeholder = st.empty()
            progress_placeholder = st.empty()
            
            statuses = ["Driver Assigned", "Driver En Route", "Picked Up", "In Transit", "Almost There", "Completed"]
            for i, status in enumerate(statuses):
                status_placeholder.markdown(f"**Status:** {status}")
                progress_placeholder.progress((i + 1) / len(statuses))
                time.sleep(1)
            
            c.execute("UPDATE bookings SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?", (booking_id,))
            c.execute("UPDATE drivers SET is_available = 1 WHERE user_id = ?", (driver[0],))
            conn.commit()
            
            st.success("✅ Ride completed!")
        else:
            st.warning("No drivers available at the moment. Please try again later.")
        
        conn.close()

def parcel_delivery():
    """Parcel delivery booking"""
    st.markdown("<div class='header-gradient'><h1>📦 Parcel Delivery</h1></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        parcel_type = st.selectbox("Parcel Type", ["Document", "Package", "Food", "Medicine", "Other"])
        weight = st.number_input("Weight (kg)", min_value=0.1, max_value=50.0, value=1.0, step=0.5)
        description = st.text_area("Description", "Brief description of the parcel")
        receiver_name = st.text_input("Receiver Name")
        receiver_phone = st.text_input("Receiver Phone")
    
    with col2:
        pickup = st.text_input("Pickup Location")
        dropoff = st.text_input("Dropoff Location")
        
        # Calculate delivery charge
        distance = random.uniform(1, 10)
        base_charge = 30
        weight_charge = weight * 10
        delivery_charge = base_charge + (distance * 5) + weight_charge
        
        st.markdown(f"""
        <div class='card'>
            <h4>Delivery Charge</h4>
            <p>Distance: {distance:.1f} km</p>
            <p>Base Charge: ₹{base_charge}</p>
            <p>Weight Charge: ₹{weight_charge:.0f}</p>
            <p><strong>Total: ₹{delivery_charge:.0f}</strong></p>
        </div>
        """, unsafe_allow_html=True)
    
    if st.button("📦 Book Delivery", use_container_width=True):
        conn = sqlite3.connect('hyperlocal.db')
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO bookings (customer_id, service_type, pickup_location, 
                                 dropoff_location, fare, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (st.session_state.user[0], 'Parcel', pickup, dropoff, delivery_charge, 'pending'))
        
        booking_id = c.lastrowid
        
        c.execute("""
            INSERT INTO parcels (booking_id, parcel_type, weight, description, 
                                receiver_name, receiver_phone)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (booking_id, parcel_type, weight, description, receiver_name, receiver_phone))
        
        conn.commit()
        st.success(f"✅ Parcel delivery booked! Booking ID: #{booking_id}")
        conn.close()

def local_services():
    """Book local services (Electrician, Plumber, etc.)"""
    st.markdown("<div class='header-gradient'><h1>🔧 Local Services</h1></div>", unsafe_allow_html=True)
    
    services_list = ["Electrician", "Plumber", "AC Repair", "Laptop Repair", "Mobile Repair", "Carpenter", "Painter"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        service_type = st.selectbox("Select Service", services_list)
        service_date = st.date_input("Service Date", min_value=datetime.now().date())
        service_time = st.time_input("Service Time", value=datetime.now().time())
        address = st.text_area("Service Address")
    
    with col2:
        st.markdown("### 💰 Service Price")
        base_prices = {
            "Electrician": 300, "Plumber": 350, "AC Repair": 500,
            "Laptop Repair": 400, "Mobile Repair": 250, "Carpenter": 450,
            "Painter": 400
        }
        price = base_prices.get(service_type, 300)
        st.markdown(f"""
        <div class='card'>
            <h3>₹{price}</h3>
            <p>Base price for {service_type}</p>
            <p><small>* Additional charges may apply based on complexity</small></p>
        </div>
        """, unsafe_allow_html=True)
    
    if st.button("🔧 Book Service", use_container_width=True):
        conn = sqlite3.connect('hyperlocal.db')
        c = conn.cursor()
        
        # Get or create service provider
        c.execute("SELECT id FROM services WHERE service_type = ? AND is_available = 1 LIMIT 1", (service_type,))
        service = c.fetchone()
        
        if not service:
            # Create a dummy service provider
            c.execute("""
                INSERT INTO services (provider_id, service_type, description, price, is_available)
                VALUES (?, ?, ?, ?, ?)
            """, (1, service_type, f"Professional {service_type} service", price, 1))
            service_id = c.lastrowid
        else:
            service_id = service[0]
        
        c.execute("""
            INSERT INTO service_bookings (service_id, customer_id, booking_date, booking_time, status)
            VALUES (?, ?, ?, ?, ?)
        """, (service_id, st.session_state.user[0], service_date, service_time, 'confirmed'))
        
        conn.commit()
        st.success(f"✅ {service_type} booked successfully!")
        conn.close()

def my_bookings():
    """View customer's bookings"""
    st.header("📋 My Bookings")
    
    conn = sqlite3.connect('hyperlocal.db')
    bookings = pd.read_sql("""
        SELECT id, service_type, pickup_location, dropoff_location, 
               fare, status, created_at, completed_at, rating
        FROM bookings 
        WHERE customer_id = ?
        ORDER BY created_at DESC
    """, conn, params=(st.session_state.user[0],))
    conn.close()
    
    if not bookings.empty:
        for _, booking in bookings.iterrows():
            status_class = f"status-{booking['status'].replace(' ', '-')}"
            st.markdown(f"""
            <div class='card'>
                <div style='display: flex; justify-content: space-between;'>
                    <div>
                        <strong>#{booking['id']}</strong> - {booking['service_type']}
                        <br>📍 {booking['pickup_location']}
                        {f"→ {booking['dropoff_location']}" if booking['dropoff_location'] else ""}
                    </div>
                    <div>
                        <span class='status-badge {status_class}'>{booking['status'].upper()}</span>
                        <br>
                        <span class='fare-badge'>₹{booking['fare']:.0f}</span>
                    </div>
                </div>
                <small>📅 {booking['created_at']}</small>
                {f"<br>⭐ Rating: {booking['rating']}/5" if booking['rating'] else ""}
            </div>
            """, unsafe_allow_html=True)
            
            # Rating button for completed rides
            if booking['status'] == 'completed' and not booking['rating']:
                rating = st.slider(f"Rate Booking #{booking['id']}", 1, 5, 5, key=f"rating_{booking['id']}")
                if st.button(f"Submit Rating", key=f"submit_rating_{booking['id']}"):
                    conn = sqlite3.connect('hyperlocal.db')
                    c = conn.cursor()
                    c.execute("UPDATE bookings SET rating = ? WHERE id = ?", (rating, booking['id']))
                    conn.commit()
                    conn.close()
                    st.success("Rating submitted! Thank you for your feedback.")
                    st.rerun()
    else:
        st.info("No bookings found")

def customer_wallet():
    """View and manage wallet"""
    st.header("💰 My Wallet")
    
    conn = sqlite3.connect('hyperlocal.db')
    
    # Get balance
    balance = pd.read_sql("""
        SELECT COALESCE(SUM(CASE WHEN transaction_type = 'credit' THEN amount ELSE -amount END), 0) as balance
        FROM wallet
        WHERE user_id = ?
    """, conn, params=(st.session_state.user[0],))['balance'][0]
    
    st.markdown(f"""
    <div class='metric-card'>
        <h3>💰 Balance</h3>
        <h2>₹{balance:.2f}</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Transactions
    transactions = pd.read_sql("""
        SELECT amount, transaction_type, description, created_at
        FROM wallet
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 20
    """, conn, params=(st.session_state.user[0],))
    
    if not transactions.empty:
        st.subheader("Recent Transactions")
        st.dataframe(transactions, use_container_width=True)
    else:
        st.info("No transactions yet")
    
    # Add money
    st.subheader("Add Money")
    amount = st.number_input("Amount (₹)", min_value=1.0, value=100.0, step=50.0)
    if st.button("Add Money"):
        conn = sqlite3.connect('hyperlocal.db')
        c = conn.cursor()
        c.execute("""
            INSERT INTO wallet (user_id, amount, transaction_type, description)
            VALUES (?, ?, ?, ?)
        """, (st.session_state.user[0], amount, 'credit', 'Added money to wallet'))
        conn.commit()
        conn.close()
        st.success(f"₹{amount} added to wallet!")
        st.rerun()
    
    conn.close()

# ==================== DRIVER FUNCTIONS ====================

def driver_dashboard():
    """Driver dashboard"""
    st.markdown("<div class='header-gradient'><h1>🚗 Driver Dashboard</h1></div>", unsafe_allow_html=True)
    
    conn = sqlite3.connect('hyperlocal.db')
    
    # Driver stats
    driver_data = pd.read_sql("""
        SELECT d.rating, d.total_rides, d.earnings, d.is_available
        FROM drivers d
        WHERE d.user_id = ?
    """, conn, params=(st.session_state.user[0],))
    
    if not driver_data.empty:
        driver = driver_data.iloc[0]
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class='metric-card'>
                <h3>⭐ Rating</h3>
                <h2>{driver['rating']:.1f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class='metric-card'>
                <h3>🚗 Total Rides</h3>
                <h2>{driver['total_rides']}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class='metric-card'>
                <h3>💰 Earnings</h3>
                <h2>₹{driver['earnings']:.0f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        # Availability toggle
        if st.button("🔄 Toggle Availability", use_container_width=True):
            conn = sqlite3.connect('hyperlocal.db')
            c = conn.cursor()
            new_status = 0 if driver['is_available'] else 1
            c.execute("UPDATE drivers SET is_available = ? WHERE user_id = ?", (new_status, st.session_state.user[0]))
            conn.commit()
            conn.close()
            st.success(f"Availability set to {'Available' if new_status else 'Offline'}")
            st.rerun()
    else:
        st.warning("Driver profile not found. Please contact admin.")
    
    conn.close()

def driver_rides():
    """View driver's rides"""
    st.header("📋 My Rides")
    
    conn = sqlite3.connect('hyperlocal.db')
    rides = pd.read_sql("""
        SELECT b.*, u.full_name as customer_name 
        FROM bookings b 
        JOIN users u ON b.customer_id = u.id 
        WHERE b.driver_id = ?
        ORDER BY b.created_at DESC
    """, conn, params=(st.session_state.user[0],))
    conn.close()
    
    if not rides.empty:
        st.dataframe(rides[['id', 'customer_name', 'service_type', 'pickup_location', 'fare', 'status', 'created_at']], 
                    use_container_width=True)
    else:
        st.info("No rides yet")

def driver_earnings():
    """View driver earnings"""
    st.header("💰 Earnings")
    
    conn = sqlite3.connect('hyperlocal.db')
    
    # Summary
    earnings_data = pd.read_sql("""
        SELECT 
            COUNT(*) as total_rides,
            SUM(fare) as total_earnings
        FROM bookings 
        WHERE driver_id = ? AND status = 'completed'
    """, conn, params=(st.session_state.user[0],))
    
    if not earnings_data.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class='metric-card'>
                <h3>🚗 Total Rides</h3>
                <h2>{earnings_data['total_rides'][0]}</h2>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class='metric-card'>
                <h3>💰 Total Earnings</h3>
                <h2>₹{earnings_data['total_earnings'][0]:.0f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        # Earnings trend
        daily = pd.read_sql("""
            SELECT DATE(created_at) as date, SUM(fare) as earnings
            FROM bookings 
            WHERE driver_id = ? AND status = 'completed'
            GROUP BY DATE(created_at)
            ORDER BY date DESC
            LIMIT 30
        """, conn, params=(st.session_state.user[0],))
        
        if not daily.empty:
            fig = px.line(daily, x='date', y='earnings', title="Daily Earnings")
            st.plotly_chart(fig, use_container_width=True)
    
    conn.close()

# ==================== LOGIN/REGISTER ====================

def login_page():
    """Login page"""
    st.markdown("<div class='header-gradient'><h1>🔑 Login</h1></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.container():
            st.markdown("### Welcome Back!")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            user_type = st.selectbox("Login as", ["customer", "driver", "admin"])
            
            if st.button("Login", use_container_width=True):
                user = authenticate_user(username, password)
                if user and user[5] == user_type:
                    st.session_state.user = user
                    st.success("✅ Login successful!")
                    time.sleep(0.5)
                    st.session_state.page = "Dashboard"
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials or user type mismatch")
            
            st.markdown("---")
            st.markdown("Don't have an account? [Register Here](#)")

def register_page():
    """Registration page"""
    st.markdown("<div class='header-gradient'><h1>📝 Register</h1></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.container():
            st.markdown("### Create New Account")
            full_name = st.text_input("Full Name")
            username = st.text_input("Username")
            phone = st.text_input("Phone Number")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            user_type = st.selectbox("Register as", ["customer", "driver"])
            
            if st.button("Register", use_container_width=True):
                if password != confirm_password:
                    st.error("❌ Passwords do not match")
                elif not all([full_name, username, phone, email, password]):
                    st.error("❌ Please fill all fields")
                else:
                    success, result = register_user(username, password, full_name, phone, email, user_type)
                    if success:
                        st.success(f"✅ Registration successful! Welcome {full_name}! {'Please wait for admin approval.' if user_type == 'driver' else 'You can now login.'}")
                    else:
                        st.error(f"❌ {result}")

# ==================== MAIN APP ====================

def main():
    """Main application entry point"""
    # Initialize database
    init_db()
    
    # Set page config and styles
    set_page_config()
    
    # Initialize session state
    if 'page' not in st.session_state:
        st.session_state.page = "Dashboard"
    
    # Show sidebar
    show_sidebar()
    
    # Check if user is logged in
    if 'user' not in st.session_state:
        if st.session_state.page == "Login":
            login_page()
        elif st.session_state.page == "Register":
            register_page()
        else:
            st.info("👋 Welcome to HyperLocal! Please login to continue.")
            login_page()
        return
    
    # Main content routing based on user type
    user_type = st.session_state.user[5]
    
    if user_type == 'admin':
        if st.session_state.page == "Dashboard":
            admin_dashboard()
        elif st.session_state.page == "Users":
            admin_users()
        elif st.session_state.page == "Drivers":
            admin_drivers()
        elif st.session_state.page == "Bookings":
            admin_bookings()
        elif st.session_state.page == "Services":
            admin_services()
        elif st.session_state.page == "Reports":
            admin_reports()
        else:
            admin_dashboard()
    
    elif user_type == 'driver':
        if st.session_state.page == "Dashboard":
            driver_dashboard()
        elif st.session_state.page == "My Rides":
            driver_rides()
        elif st.session_state.page == "Earnings":
            driver_earnings()
        else:
            driver_dashboard()
    
    else:  # customer
        if st.session_state.page == "Dashboard":
            customer_dashboard()
        elif st.session_state.page == "Book Ride":
            book_ride()
        elif st.session_state.page == "Parcel Delivery":
            parcel_delivery()
        elif st.session_state.page == "Local Services":
            local_services()
        elif st.session_state.page == "My Bookings":
            my_bookings()
        elif st.session_state.page == "Wallet":
            customer_wallet()
        else:
            customer_dashboard()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #888; padding: 20px;'>
        <p>HyperLocal Ride Booking © 2025 | Made with ❤️</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()