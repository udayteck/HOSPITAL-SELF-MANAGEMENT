import pymysql

try:
    conn = pymysql.connect(
        host='localhost',
        user='hospital_user',
        password='Test12345',   # Simple password
        database='hospital'
    )
    print("✅ SUCCESS! Connected to MySQL")
    conn.close()
except Exception as e:
    print(f"❌ FAILED: {e}")