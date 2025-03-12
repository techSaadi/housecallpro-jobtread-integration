from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# API Keys & URLs from .env
HOUSECALL_PRO_API_KEY = os.getenv("HOUSECALL_PRO_API_KEY")
HOUSECALL_PRO_API_URL = os.getenv("HOUSECALL_PRO_API_URL")
JOBTREAD_API_KEY = os.getenv("JOBTREAD_API_KEY")
JOBTREAD_API_URL = os.getenv("JOBTREAD_API_URL")

# Function to create a customer in JobTread
def create_customer_in_jobtread(customer_data):
    url = f"{JOBTREAD_API_URL}/customers"
    headers = {
        "Authorization": f"Bearer {JOBTREAD_API_KEY}",
        "Content-Type": "application/json"
    }

    # Ensure required fields are present
    required_fields = ["first_name", "last_name", "email", "phone"]
    if not all(field in customer_data for field in required_fields):
        print("Error: Missing required fields for creating a customer in JobTread.")
        return False

    response = requests.post(url, json=customer_data, headers=headers)

    print("JobTread API Response:", response.status_code, response.text)
    return response.status_code == 201

# Function to create a job in JobTread
def create_job_in_jobtread(job_data):
    url = f"{JOBTREAD_API_URL}/jobs"
    headers = {
        "Authorization": f"Bearer {JOBTREAD_API_KEY}",
        "Content-Type": "application/json"
    }

    # Ensure required fields are present
    required_fields = ["name", "customer_id", "address"]
    if not all(field in job_data for field in required_fields):
        print("Error: Missing required fields for creating a job in JobTread.")
        return False

    response = requests.post(url, json=job_data, headers=headers)

    print("JobTread API Response:", response.status_code, response.text)
    return response.status_code == 201

# Webhook endpoint for Housecall Pro
@app.route("/housecallpro-webhook", methods=["POST"])
def housecallpro_webhook():
    try:
        data = request.json
        print("Received raw data from Housecall Pro:", data)

        if data is None:
            print("Error: No data received in the request.")
            return jsonify({"status": "error", "message": "No data received"}), 400

        # Extract event type
        event_type = data.get("event")
        print("Event Type:", event_type)

        # Log the entire payload for debugging
        print("Full Payload:", data)

        # Handle the test payload
        if data == {"foo": "bar"}:
            print("Received test payload from Housecall Pro.")
            return jsonify({"status": "success", "message": "Test webhook received"}), 200

        # Handle supported event types
        if event_type in ["customer.created", "customer.updated", "job.created", "job.updated", "estimate.approved", "estimate.created"]:
            print(f"Processing {event_type} event.")
            return jsonify({"status": "success", "message": f"Processed {event_type} event"}), 200
        else:
            print("Error: Unsupported event type.")
            return jsonify({"status": "error", "message": "Unsupported event type"}), 400

    except Exception as e:
        print(f"Exception in housecallpro_webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

        

# Root route
@app.route("/")
def home():
    return "Integration Server is Running!"

# Run the Flask app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use Render's PORT variable
    app.run(host="0.0.0.0", port=port)
