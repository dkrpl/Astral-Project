import socket
import pymysql
import requests
import json
from urllib.parse import urlparse

def test_mysql_connection(host, port, username, password, database):
    print("🔍 Testing MySQL Connection...")
    
    # Test DNS Resolution
    try:
        ip = socket.gethostbyname(host)
        print(f"✅ DNS Resolution: {host} -> {ip}")
    except socket.gaierror as e:
        print(f"❌ DNS Resolution Failed: {e}")
        return False

    # Test Port Connectivity
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✅ Port {port} is open")
        else:
            print(f"❌ Port {port} is closed (error: {result})")
            return False
    except Exception as e:
        print(f"❌ Port test failed: {e}")
        return False

    # Test MySQL Connection
    try:
        connection = pymysql.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database,
            connect_timeout=20,
            read_timeout=30
        )
        print("✅ MySQL Connection: SUCCESS")
        
        # Test basic query
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"✅ Database accessible. Found {len(tables)} tables")
        
        connection.close()
        return True
        
    except pymysql.Error as e:
        print(f"❌ MySQL Connection Failed: {e}")
        return False

# Test your connection
if __name__ == "__main__":
    config = {
        "host": "bmtmuamalatnurulhuda.com",
        "port": 3306,
        "username": "bmtw6961_bmtw6961", 
        "password": "bmtw6961@2023",
        "database": "bmtw6961_OBS"
    }
    
    test_mysql_connection(**config)