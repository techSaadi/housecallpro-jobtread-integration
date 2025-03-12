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
        print("Received data from Housecall Pro:", data)

        if data is None:
            print("Error: No data received in the request.")
            return jsonify({"status": "error", "message": "No data received"}), 400

        # Extract event type
        event_type = data.get("event")
        print("Event Type:", event_type)

        if event_type == "customer.updated" or event_type == "customer.created":
            # Handle customer updated/created event
            customer_data = data.get("customer", {})
            print("Processing customer:", customer_data)

            # Prepare customer data for JobTread
            jobtread_customer_data = {
                "first_name": customer_data.get("first_name"),
                "last_name": customer_data.get("last_name"),
                "email": customer_data.get("email"),
                "phone": customer_data.get("mobile_number"),
                "address": customer_data.get("addresses", [{}])[0].get("street"),  # Use the first address
                # Add other required fields for JobTread
            }

            # Sync customer to JobTread
            if create_customer_in_jobtread(jobtread_customer_data):
                print("Customer successfully synced to JobTread.")
                return jsonify({"status": "success"}), 200
            else:
                print("Failed to sync customer to JobTread.")
                return jsonify({"status": "error", "message": "Failed to sync customer"}), 500

        elif event_type == "job.created" or event_type == "job.updated":
            # Handle job created/updated event
            job_data = data.get("job", {})
            print("Processing job:", job_data)

            # Prepare job data for JobTread
            jobtread_job_data = {
                "name": job_data.get("name"),
                "customer_id": job_data.get("customer_id"),
                "address": job_data.get("address"),
                # Add other required fields for JobTread
            }

            # Sync job to JobTread
            if create_job_in_jobtread(jobtread_job_data):
                print("Job successfully synced to JobTread.")
                return jsonify({"status": "success"}), 200
            else:
                print("Failed to sync job to JobTread.")
                return jsonify({"status": "error", "message": "Failed to sync job"}), 500

        elif event_type == "estimate.approved" or event_type == "estimate.created":
            # Handle estimate approved/created event
            estimate_data = data.get("estimate", {})
            print("Processing estimate:", estimate_data)

            # Prepare job data for JobTread (convert estimate to job)
            jobtread_job_data = {
                "name": estimate_data.get("name"),
                "customer_id": estimate_data.get("customer_id"),
                "address": estimate_data.get("address"),
                # Add other required fields for JobTread
            }

            # Sync job to JobTread
            if create_job_in_jobtread(jobtread_job_data):
                print("Estimate successfully converted to job in JobTread.")
                return jsonify({"status": "success"}), 200
            else:
                print("Failed to convert estimate to job in JobTread.")
                return jsonify({"status": "error", "message": "Failed to convert estimate"}), 500

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
