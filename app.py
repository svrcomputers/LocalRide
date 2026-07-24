"""
Hyper Local Ride Booking Application - FULL VERSION
Complete ride booking, parcel delivery, and local services platform.
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
import os
import traceback

# ==================== DATABASE SETUP ====================

def init_db():
    """Initialize SQLite database with all required tables"""
    try:
        conn = sqlite3.connect('hyperlocal.db')
        c = conn.cursor()
        
        # Users table
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
        
        # Drivers table
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
        
        # Parcels table
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
        
        # Services table
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
        
        # Wallet
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
        
        # Get driver id and create driver profile
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
        c.execute("SELECT * FROM users WHERE username = 'admin'")
        if c.fetchone():
            print("✅ Admin created successfully!")
        else:
            print("❌ Admin creation failed!")
        
        conn.close()
        return True
    except Exception as e:
        print(f"Database initialization error: {e}")
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
        print(f"Authentication error: {e}")
        return None

def register_user(username, password, full_name, phone, email, user_type):
    try:
        conn = sqlite3.connect('hyperlocal.db')
        c = conn.cursor()
        hashed = hash_password(password)
        c.execute("INSERT INTO users (username, password, full_name, phone, email, user_type, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (username, hashed, full_name, phone, email, user_type, 'pending' if user_type == 'driver' else 'approved'))
        user_id = c.lastrowid
        
        if user_type == 'driver':
            c.execute("INSERT INTO drivers (user_id, vehicle_type, vehicle_number, license_number) VALUES (?, ?, ?, ?)",
                     (user_id, 'bike', 'TN01AB1234', 'DL1234567890'))
        
        conn.commit()
        conn.close()
        return True, user_id
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    except Exception as e:
        return False, str(e)

# ==================== UI COMPONENTS ====================

def set_page_config():
    """Configure Streamlit page"""
    st.set_page_config(
        page_title="HyperLocal Ride Booking",
        page_icon="🚗",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown("""
    <style>
        .main { background-color: #ffffff; }
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
        .status-badge {
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .status-pending { background: #fff3cd; color: #856404; }
        .status-approved { background: #d4edda; color: #155724; }
        .status-completed { background: #cce5ff; color: #004085; }
        .status-in-progress { background: #d1ecf1; color: #0c5460; }
        .fare-badge {
            background: #1a73e8;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
        }
        .login-container {
            max-width: 450px;
            margin: 0 auto;
            padding: 30px;
            background: white;
            border-radius: 15px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        h1, h2, h3 { color: #1a73e8; }
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
                menu = ["Dashboard", "Users", "Drivers", "Bookings", "Services", "Reports"]
                icons = ["📊", "👥", "🚗", "📋", "🔧", "📈"]
            elif st.session_state.user[5] == 'driver':
                menu = ["Dashboard", "My Rides", "Earnings", "Availability"]
                icons = ["📊", "🚗", "💰", "🔄"]
            else:
                menu = ["Dashboard", "Book Ride", "Parcel Delivery", "Local Services", "My Bookings", "Wallet"]
                icons = ["📊", "🚗", "📦", "🔧", "📋", "💰"]
            
            for i, item in enumerate(menu):
                if st.button(f"{icons[i]} {item}", key=f"nav_{item}"):
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
    
    try:
        conn = sqlite3.connect('hyperlocal.db')
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_users = pd.read_sql("SELECT COUNT(*) as count FROM users WHERE user_type != 'admin'", conn)['count'][0]
            st.markdown(f"""<div class='metric-card'><h3>👥 Users</h3><h2>{total_users}</h2></div>""", unsafe_allow_html=True)
        
        with col2:
            total_drivers = pd.read_sql("SELECT COUNT(*) as count FROM users WHERE user_type = 'driver'", conn)['count'][0]
            st.markdown(f"""<div class='metric-card'><h3>🚗 Drivers</h3><h2>{total_drivers}</h2></div>""", unsafe_allow_html=True)
        
        with col3:
            total_bookings = pd.read_sql("SELECT COUNT(*) as count FROM bookings", conn)['count'][0]
            st.markdown(f"""<div class='metric-card'><h3>📋 Bookings</h3><h2>{total_bookings}</h2></div>""", unsafe_allow_html=True)
        
        with col4:
            revenue = pd.read_sql("SELECT SUM(fare) as total FROM bookings WHERE status = 'completed'", conn)['total'][0] or 0
            st.markdown(f"""<div class='metric-card'><h3>💰 Revenue</h3><h2>₹{revenue:,.0f}</h2></div>""", unsafe_allow_html=True)
        
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
            service_df = pd.read_sql("SELECT service_type, COUNT(*) as count FROM bookings GROUP BY service_type", conn)
            if not service_df.empty:
                fig = px.pie(service_df, values='count', names='service_type', title="Bookings by Service")
                st.plotly_chart(fig, use_container_width=True)
        
        conn.close()
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")

def admin_users():
    st.header("👥 User Management")
    try:
        conn = sqlite3.connect('hyperlocal.db')
        users = pd.read_sql("SELECT id, username, full_name, phone, user_type, status, created_at FROM users", conn)
        conn.close()
        st.dataframe(users, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")

def admin_drivers():
    st.header("🚗 Driver Management")
    try:
        conn = sqlite3.connect('hyperlocal.db')
        drivers = pd.read_sql("""
            SELECT u.id, u.username, u.full_name, u.phone, u.status, 
                   d.vehicle_type, d.vehicle_number, d.rating, d.total_rides, d.earnings
            FROM users u JOIN drivers d ON u.id = d.user_id WHERE u.user_type = 'driver'
        """, conn)
        conn.close()
        st.dataframe(drivers, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")

def admin_bookings():
    st.header("📋 All Bookings")
    try:
        conn = sqlite3.connect('hyperlocal.db')
        bookings = pd.read_sql("SELECT * FROM bookings ORDER BY created_at DESC", conn)
        conn.close()
        st.dataframe(bookings, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")

def admin_services():
    st.header("🔧 Services")
    try:
        conn = sqlite3.connect('hyperlocal.db')
        services = pd.read_sql("SELECT * FROM services", conn)
        conn.close()
        st.dataframe(services, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")

def admin_reports():
    st.header("📈 Reports")
    try:
        conn = sqlite3.connect('hyperlocal.db')
        revenue_data = pd.read_sql("""
            SELECT DATE(created_at) as date, COUNT(*) as bookings, SUM(fare) as revenue
            FROM bookings WHERE status = 'completed'
            GROUP BY DATE(created_at) ORDER BY date DESC LIMIT 30
        """, conn)
        conn.close()
        
        if not revenue_data.empty:
            fig = px.bar(revenue_data, x='date', y=['bookings', 'revenue'], title="Daily Revenue")
            st.plotly_chart(fig, use_container_width=True)
            
            csv = revenue_data.to_csv(index=False)
            st.download_button("📥 Download Report", csv, f"report_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
        else:
            st.info("No data available")
    except Exception as e:
        st.error(f"Error: {e}")

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
    
    try:
        conn = sqlite3.connect('hyperlocal.db')
        recent = pd.read_sql("""
            SELECT id, service_type, pickup_location, fare, status, created_at
            FROM bookings WHERE customer_id = ?
            ORDER BY created_at DESC LIMIT 5
        """, conn, params=(st.session_state.user[0],))
        conn.close()
        
        st.subheader("📋 Recent Bookings")
        if not recent.empty:
            for _, booking in recent.iterrows():
                st.markdown(f"""
                <div class='card'>
                    <div style='display: flex; justify-content: space-between;'>
                        <div><strong>#{booking['id']}</strong> - {booking['service_type']}<br>📍 {booking['pickup_location']}</div>
                        <div><span class='fare-badge'>₹{booking['fare']:.0f}</span><br><small>{booking['status'].upper()}</small></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No bookings yet")
    except Exception as e:
        st.error(f"Error loading bookings: {e}")

def book_ride():
    st.markdown("<div class='header-gradient'><h1>🚗 Book a Ride</h1></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
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
    
    with col2:
        st.markdown("### 📍 Map")
        try:
            m = folium.Map(location=[12.9716, 77.5946], zoom_start=12)
            folium.Marker([12.9716, 77.5946], popup="Your Location").add_to(m)
            st_folium(m, width=400, height=300)
        except:
            st.info("📍 Location: 12.9716° N, 77.5946° E")
    
    if st.button("🚗 Book Now", use_container_width=True):
        try:
            conn = sqlite3.connect('hyperlocal.db')
            c = conn.cursor()
            
            # Find available driver
            c.execute("""
                SELECT u.id FROM users u 
                JOIN drivers d ON u.id = d.user_id 
                WHERE u.status = 'approved' AND d.is_available = 1 
                AND d.vehicle_type = ? LIMIT 1
            """, (service_type.lower(),))
            
            driver = c.fetchone()
            
            if driver:
                c.execute("""INSERT INTO bookings (customer_id, driver_id, service_type, pickup_location, 
                             dropoff_location, fare, distance, status)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                         (st.session_state.user[0], driver[0], service_type, pickup, dropoff, fare, distance, 'in-progress'))
                
                booking_id = c.lastrowid
                c.execute("UPDATE drivers SET is_available = 0 WHERE user_id = ?", (driver[0],))
                conn.commit()
                
                st.success(f"✅ Ride booked! #{booking_id}")
                progress = st.progress(0)
                for i in range(6):
                    time.sleep(0.5)
                    progress.progress((i + 1) / 6)
                
                c.execute("UPDATE bookings SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?", (booking_id,))
                c.execute("UPDATE drivers SET is_available = 1 WHERE user_id = ?", (driver[0],))
                conn.commit()
                st.success("✅ Ride completed!")
            else:
                st.warning("No drivers available")
            
            conn.close()
        except Exception as e:
            st.error(f"Error booking ride: {e}")

def parcel_delivery():
    st.markdown("<div class='header-gradient'><h1>📦 Parcel Delivery</h1></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        parcel_type = st.selectbox("Parcel Type", ["Document", "Package", "Food", "Medicine"])
        weight = st.number_input("Weight (kg)", min_value=0.1, max_value=50.0, value=1.0)
        receiver_name = st.text_input("Receiver Name")
        receiver_phone = st.text_input("Receiver Phone")
    
    with col2:
        pickup = st.text_input("Pickup Location")
        dropoff = st.text_input("Dropoff Location")
        distance = random.uniform(1, 10)
        delivery_charge = 30 + (distance * 5) + (weight * 10)
        
        st.markdown(f"""
        <div class='card'>
            <h4>Delivery Charge</h4>
            <p>Distance: {distance:.1f} km</p>
            <p><strong>₹{delivery_charge:.0f}</strong></p>
        </div>
        """, unsafe_allow_html=True)
    
    if st.button("📦 Book Delivery", use_container_width=True):
        try:
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
        except Exception as e:
            st.error(f"Error: {e}")

def local_services():
    st.markdown("<div class='header-gradient'><h1>🔧 Local Services</h1></div>", unsafe_allow_html=True)
    
    services_list = ["Electrician", "Plumber", "AC Repair", "Laptop Repair", "Mobile Repair"]
    service_type = st.selectbox("Select Service", services_list)
    
    base_prices = {"Electrician": 300, "Plumber": 350, "AC Repair": 500, "Laptop Repair": 400, "Mobile Repair": 250}
    price = base_prices.get(service_type, 300)
    
    col1, col2 = st.columns(2)
    with col1:
        service_date = st.date_input("Date", min_value=datetime.now().date())
        service_time = st.time_input("Time", value=datetime.now().time())
    with col2:
        st.markdown(f"""
        <div class='card'>
            <h3>₹{price}</h3>
            <p>Base price for {service_type}</p>
        </div>
        """, unsafe_allow_html=True)
        address = st.text_area("Address")
    
    if st.button("🔧 Book Service", use_container_width=True):
        try:
            conn = sqlite3.connect('hyperlocal.db')
            c = conn.cursor()
            c.execute("SELECT id FROM services WHERE service_type = ? LIMIT 1", (service_type,))
            service = c.fetchone()
            
            if not service:
                c.execute("INSERT INTO services (provider_id, service_type, price, is_available) VALUES (?, ?, ?, ?)",
                         (1, service_type, price, 1))
                service_id = c.lastrowid
            else:
                service_id = service[0]
            
            c.execute("""INSERT INTO service_bookings (service_id, customer_id, booking_date, booking_time, status)
                         VALUES (?, ?, ?, ?, ?)""",
                     (service_id, st.session_state.user[0], service_date, service_time, 'confirmed'))
            conn.commit()
            conn.close()
            st.success(f"✅ {service_type} booked!")
        except Exception as e:
            st.error(f"Error: {e}")

def my_bookings():
    st.header("📋 My Bookings")
    
    try:
        conn = sqlite3.connect('hyperlocal.db')
        bookings = pd.read_sql("""
            SELECT id, service_type, pickup_location, fare, status, created_at
            FROM bookings WHERE customer_id = ?
            ORDER BY created_at DESC
        """, conn, params=(st.session_state.user[0],))
        conn.close()
        
        if not bookings.empty:
            st.dataframe(bookings, use_container_width=True)
        else:
            st.info("No bookings")
    except Exception as e:
        st.error(f"Error: {e}")

def customer_wallet():
    st.header("💰 My Wallet")
    
    try:
        conn = sqlite3.connect('hyperlocal.db')
        balance = pd.read_sql("""
            SELECT COALESCE(SUM(CASE WHEN transaction_type = 'credit' THEN amount ELSE -amount END), 0) as balance
            FROM wallet WHERE user_id = ?
        """, conn, params=(st.session_state.user[0],))['balance'][0]
        conn.close()
        
        st.markdown(f"""<div class='metric-card'><h3>💰 Balance</h3><h2>₹{balance:.2f}</h2></div>""", unsafe_allow_html=True)
        
        amount = st.number_input("Add Money (₹)", min_value=1.0, max_value=10000.0, value=100.0)
        if st.button("Add Money", use_container_width=True):
            conn = sqlite3.connect('hyperlocal.db')
            c = conn.cursor()
            c.execute("INSERT INTO wallet (user_id, amount, transaction_type, description) VALUES (?, ?, ?, ?)",
                     (st.session_state.user[0], amount, 'credit', 'Added money'))
            conn.commit()
            conn.close()
            st.success(f"₹{amount} added!")
            st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

# ==================== DRIVER FUNCTIONS ====================

def driver_dashboard():
    st.markdown("<div class='header-gradient'><h1>🚗 Driver Dashboard</h1></div>", unsafe_allow_html=True)
    
    try:
        conn = sqlite3.connect('hyperlocal.db')
        driver_data = pd.read_sql("""
            SELECT rating, total_rides, earnings, is_available
            FROM drivers WHERE user_id = ?
        """, conn, params=(st.session_state.user[0],))
        
        if not driver_data.empty:
            driver = driver_data.iloc[0]
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""<div class='metric-card'><h3>⭐ Rating</h3><h2>{driver['rating']:.1f}</h2></div>""", unsafe_allow_html=True)
            with col2:
                st.markdown(f"""<div class='metric-card'><h3>🚗 Rides</h3><h2>{driver['total_rides']}</h2></div>""", unsafe_allow_html=True)
            with col3:
                st.markdown(f"""<div class='metric-card'><h3>💰 Earnings</h3><h2>₹{driver['earnings']:.0f}</h2></div>""", unsafe_allow_html=True)
            
            if st.button("🔄 Toggle Availability", use_container_width=True):
                new_status = 0 if driver['is_available'] else 1
                conn = sqlite3.connect('hyperlocal.db')
                c = conn.cursor()
                c.execute("UPDATE drivers SET is_available = ? WHERE user_id = ?", (new_status, st.session_state.user[0]))
                conn.commit()
                conn.close()
                st.success(f"{'Available' if new_status else 'Offline'}")
                st.rerun()
        else:
            st.warning("Driver profile not found")
        
        conn.close()
    except Exception as e:
        st.error(f"Error: {e}")

def driver_rides():
    st.header("📋 My Rides")
    try:
        conn = sqlite3.connect('hyperlocal.db')
        rides = pd.read_sql("""
            SELECT b.*, u.full_name as customer_name 
            FROM bookings b JOIN users u ON b.customer_id = u.id 
            WHERE b.driver_id = ? ORDER BY b.created_at DESC
        """, conn, params=(st.session_state.user[0],))
        conn.close()
        st.dataframe(rides, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")

def driver_earnings():
    st.header("💰 Earnings")
    try:
        conn = sqlite3.connect('hyperlocal.db')
        earnings = pd.read_sql("""
            SELECT DATE(created_at) as date, SUM(fare) as earnings
            FROM bookings WHERE driver_id = ? AND status = 'completed'
            GROUP BY DATE(created_at) ORDER BY date DESC LIMIT 30
        """, conn, params=(st.session_state.user[0],))
        conn.close()
        
        if not earnings.empty:
            fig = px.line(earnings, x='date', y='earnings', title="Earnings Trend")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No earnings data")
    except Exception as e:
        st.error(f"Error: {e}")

# ==================== LOGIN/REGISTER ====================

def login_page():
    st.markdown("<div class='header-gradient'><h1>🔑 Login</h1></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.container():
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            st.markdown("### Welcome Back!")
            
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
                            if user[6] == 'approved':
                                st.session_state.user = user
                                st.success("✅ Login successful!")
                                st.session_state.page = "Dashboard"
                                st.rerun()
                            else:
                                st.error("❌ Account pending approval")
                        else:
                            st.error("❌ User type mismatch")
                    else:
                        st.error("❌ Invalid credentials")
            
            st.markdown("---")
            if st.button("📝 Register instead"):
                st.session_state.page = "Register"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

def register_page():
    st.markdown("<div class='header-gradient'><h1>📝 Register</h1></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.container():
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            st.markdown("### Create Account")
            
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
                elif not all([full_name, username, phone, email]):
                    st.error("❌ Fill all fields")
                else:
                    success, result = register_user(username, password, full_name, phone, email, user_type)
                    if success:
                        st.success(f"✅ Registered! {'Wait for admin approval.' if user_type == 'driver' else 'You can login now.'}")
                    else:
                        st.error(f"❌ {result}")
            
            if st.button("🔑 Login instead"):
                st.session_state.page = "Login"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# ==================== MAIN APP ====================

def main():
    """Main application entry point"""
    # Initialize database
    try:
        init_db()
    except Exception as e:
        st.error(f"Database initialization error: {e}")
        return
    
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
    
    try:
        if user_type == 'admin':
            if st.session_state.page == "Dashboard": admin_dashboard()
            elif st.session_state.page == "Users": admin_users()
            elif st.session_state.page == "Drivers": admin_drivers()
            elif st.session_state.page == "Bookings": admin_bookings()
            elif st.session_state.page == "Services": admin_services()
            elif st.session_state.page == "Reports": admin_reports()
            else: admin_dashboard()
        
        elif user_type == 'driver':
            if st.session_state.page == "Dashboard": driver_dashboard()
            elif st.session_state.page == "My Rides": driver_rides()
            elif st.session_state.page == "Earnings": driver_earnings()
            else: driver_dashboard()
        
        else:  # customer
            if st.session_state.page == "Dashboard": customer_dashboard()
            elif st.session_state.page == "Book Ride": book_ride()
            elif st.session_state.page == "Parcel Delivery": parcel_delivery()
            elif st.session_state.page == "Local Services": local_services()
            elif st.session_state.page == "My Bookings": my_bookings()
            elif st.session_state.page == "Wallet": customer_wallet()
            else: customer_dashboard()
    except Exception as e:
        st.error(f"Error: {e}")
        st.code(traceback.format_exc())
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #888; padding: 20px;'>
        <p>HyperLocal Ride Booking © 2025 | Made with ❤️</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
