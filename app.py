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

# Function to create a customer in Housecall Pro
def create_customer_in_housecallpro(customer_data):
    url = f"{HOUSECALL_PRO_API_URL}/customers"
    headers = {
        "Authorization": f"Bearer {HOUSECALL_PRO_API_KEY}",
        "Content-Type": "application/json"
    }

    # Ensure at least one required field is present
    required_fields = ["name", "email", "phone"]
    if not any(field in customer_data for field in required_fields):
        print("Error: Customer must have one of name, email, or phone number.")
        return False

    response = requests.post(url, json=customer_data, headers=headers)

    print("Housecall Pro API Response:", response.status_code, response.text)
    return response.status_code == 201

# Function to create a job in Housecall Pro
def create_job_in_housecallpro(job_data):
    url = f"{HOUSECALL_PRO_API_URL}/jobs"
    headers = {
        "Authorization": f"Bearer {HOUSECALL_PRO_API_KEY}",
        "Content-Type": "application/json"
    }

    # Ensure required fields are present
    required_fields = ["customer_id", "name", "address"]
    if not all(field in job_data for field in required_fields):
        print("Error: Missing required fields for creating a job.")
        return False

    response = requests.post(url, json=job_data, headers=headers)

    print("Housecall Pro API Response:", response.status_code, response.text)
    return response.status_code == 201

# Function to create an estimate in Housecall Pro
def create_estimate_in_housecallpro(estimate_data):
    url = f"{HOUSECALL_PRO_API_URL}/estimates"
    headers = {
        "Authorization": f"Bearer {HOUSECALL_PRO_API_KEY}",
        "Content-Type": "application/json"
    }

    # Ensure required fields are present
    required_fields = ["customer_id", "job_id", "total_amount"]
    if not all(field in estimate_data for field in required_fields):
        print("Error: Missing required fields for creating an estimate.")
        return False

    response = requests.post(url, json=estimate_data, headers=headers)

    print("Housecall Pro API Response:", response.status_code, response.text)
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

# Webhook endpoint for JobTread
@app.route("/jobtread-webhook", methods=["POST"])
def jobtread_webhook():
    try:
        data = request.json
        print("Received raw data from JobTread:", data)

        if data is None:
            print("Error: No data received in the request.")
            return jsonify({"status": "error", "message": "No data received"}), 400

        # Check for 'createdEvent' key
        created_event = data.get("createdEvent")
        if not created_event:
            print("Error: 'createdEvent' key is missing in the payload.")
            return jsonify({"status": "error", "message": "Missing 'createdEvent' key"}), 400

        # Extract event type
        event_type = created_event.get("type")
        print("Extracted Event Type:", event_type)

        if event_type is None:
            print("Warning: Event type is None. Attempting to infer event type.")
            if "contact" in created_event:
                event_type = "customerCreated"
            elif "job" in created_event:
                event_type = "jobCreated"
            elif "estimate" in created_event:
                event_type = "estimateCreated"
            elif "file" in created_event:
                event_type = "fileCreated"
            else:
                print("Error: Unable to infer event type from the data.")
                return jsonify({"status": "error", "message": "Unable to infer event type"}), 400

        print("Processing Event Type:", event_type)

        # Handle the event based on its type
        if event_type == "fileCreated" or event_type == "fileUpdated":
            file_data = created_event.get("file", {})
            job = created_event.get("job", {})
            location = created_event.get("location", {})

            print("File Data:", file_data)
            print("Job Data:", job)
            print("Location Data:", location)

            # Add your logic here to handle the file event
            print(f"Handling {event_type} event for file: {file_data.get('name')}")

            return jsonify({"status": "success"}), 200

        else:
            print("Error: Unsupported event type.")
            return jsonify({"status": "error", "message": "Unsupported event type"}), 400

    except Exception as e:
        print(f"Exception in jobtread_webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Webhook endpoint for Housecall Pro
@app.route("/housecallpro-webhook", methods=["POST"])
def housecallpro_webhook():
    try:
        data = request.json
        print("Received raw data from Housecall Pro:", data)

        # Debug: Check if data is None
        if data is None:
            print("Error: No data received in the request.")
            return jsonify({"status": "error", "message": "No data received"}), 400

        # Handle the test payload
        if data == {"foo": "bar"}:
            print("Received test payload from Housecall Pro.")
            return jsonify({"status": "success", "message": "Test webhook received"}), 200

        # Extract event type
        event_type = data.get("event")
        print("Event Type:", event_type)

        if event_type == "job.created":
            # Handle job created event
            job_data = data.get("job", {})
            print("Processing new job:", job_data)

            # Sync job to JobTread
            jobtread_job_data = {
                "name": job_data.get("name"),
                "customer_id": job_data.get("customer_id"),
                "address": job_data.get("address"),
                # Add other required fields for JobTread
            }

            if create_job_in_jobtread(jobtread_job_data):
                print("Job successfully synced to JobTread.")
                return jsonify({"status": "success"}), 200
            else:
                print("Failed to sync job to JobTread.")
                return jsonify({"status": "error", "message": "Failed to sync job"}), 500

        elif event_type == "estimate.approved":
            # Handle estimate approved event
            estimate_data = data.get("estimate", {})
            print("Processing approved estimate:", estimate_data)

            # Convert estimate to job in JobTread
            jobtread_job_data = {
                "name": estimate_data.get("name"),
                "customer_id": estimate_data.get("customer_id"),
                "address": estimate_data.get("address"),
                # Add other required fields for JobTread
            }

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
