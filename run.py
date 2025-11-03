from __init__ import create_app
import os

app = create_app(os.environ.get('FLASK_ENV', 'production'))

if __name__ == "__main__":
    print("🚀 Starting Money Transfer API...")
    print("📍 Server running on: http://localhost:5000")
    print("📍 Health check: http://localhost:5000/api/health")
    print("👤 Default admin: admin@example.com / admin123")
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)