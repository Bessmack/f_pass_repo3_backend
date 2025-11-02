from __init__ import create_app

app = create_app('development')

if __name__ == "__main__":
    print("🚀 Starting Money Transfer API...")
    print("📍 Server running on: http://localhost:5000")
    print("📍 Health check: http://localhost:5000/api/health")
    print("👤 Default admin: admin@example.com / admin123")
    
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )