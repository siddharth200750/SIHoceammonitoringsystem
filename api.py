from flask import Flask, jsonify
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
# Allow cross-origin requests so your local HTML file can fetch the data
CORS(app)  

DB_NAME = "ocean_alerts.db"

def get_all_alerts():
    """Reads the SQLite database and formats it as a list of dictionaries."""
    conn = sqlite3.connect(DB_NAME)
    # This row_factory makes SQLite return rows as dictionaries instead of tuples
    conn.row_factory = sqlite3.Row  
    cursor = conn.cursor()
    
    # Fetch all alerts that have valid coordinates
    cursor.execute('''
        SELECT id, source_platform, title, published_at, 
               source_url, location_name, latitude, longitude, severity 
        FROM alerts 
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        ORDER BY id DESC
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    # Convert sqlite3.Row objects to standard Python dictionaries
    return [dict(row) for row in rows]

@app.route('/api/alerts', methods=['GET'])
def serve_alerts():
    """The endpoint the frontend map will hi to get the markers."""
    data = get_all_alerts()
    return jsonify({
        "status": "success",
        "total_alerts": len(data),
        "data": data
    })

if __name__ == '__main__':
    # Run the server on port 5000
    print(" Starting API server on http://localhost:5000/api/alerts")
    app.run(debug=True, port=5000)