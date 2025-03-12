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

# Function to create a job in JobTread
def create_job_in_jobtread(job_data):
    url = f"{JOBTREAD_API_URL}/jobs"
    headers = {
        "Authorization": f"Bearer {JOBTREAD_API_KEY}",
        "Content-Type": "application/json"
    }

    # Ensure required fields are present
    required_fields = ["customer_id", "name", "address"]
    if not all(field in job_data for field in required_fields):
        print("Error: Missing required fields for creating a job.")
        return False

    response = requests.post(url, json=job_data, headers=headers)

    print("JobTread API Response:", response.status_code, response.text)
    return response.status_code == 201

# Webhook endpoint for JobTread
@app.route("/jobtread-webhook", methods=["POST"])
def jobtread_webhook():
    try:
        data = request.json
        print("Received raw data from JobTread:", data)  # Log raw data

        if data is None:
            print("Warning: No data received in the request.")
            return jsonify({"status": "success", "message": "No data received"}), 200

        # Check for 'createdEvent' key
        created_event = data.get("createdEvent")
        if not created_event:
            print("Warning: 'createdEvent' key is missing in the payload.")
            return jsonify({"status": "success", "message": "Missing 'createdEvent' key"}), 200

        # Extract event type
        event_type = created_event.get("type")
        print("Extracted Event Type:", event_type)  # Log the extracted event type

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
                print("Warning: Unable to infer event type from the data.")
                return jsonify({"status": "success", "message": "Unable to infer event type"}), 200

        print("Processing Event Type:", event_type)

        # Handle the event based on its type
        if event_type == "jobCreated":
            job_data = created_event.get("job", {})
            print("Job Data:", job_data)

            # Map JobTread job data to Housecall Pro job data
            housecallpro_job_data = {
                "customer_id": job_data.get("customer_id"),
                "name": job_data.get("name"),
                "address": job_data.get("address"),
                # Add other necessary fields
            }

            # Create the job in Housecall Pro
            if create_job_in_housecallpro(housecallpro_job_data):
                print("Job successfully created in Housecall Pro.")
            else:
                print("Failed to create job in Housecall Pro.")

        else:
            print("Warning: Unsupported event type.")

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"Exception in jobtread_webhook: {e}")
        return jsonify({"status": "success", "message": str(e)}), 200

# Webhook endpoint for Housecall Pro
@app.route("/housecallpro-webhook", methods=["POST"])
def housecallpro_webhook():
    try:
        data = request.json
        print("Received data from Housecall Pro:", data)

        # Debug: Check if data is None
        if data is None:
            print("Warning: No data received in the request.")
            return jsonify({"status": "success", "message": "No data received"}), 200

        # Extract event type
        event_type = data.get("event")
        print("Event Type:", event_type)

        if event_type == "job.created":
            # Handle job created event
            job_data = data.get("job", {})
            print("Processing created job:", job_data)

            # Map Housecall Pro job data to JobTread job data
            jobtread_job_data = {
                "customer_id": job_data.get("customer_id"),
                "name": job_data.get("name"),
                "address": job_data.get("address"),
                # Add other necessary fields
            }

            # Create the job in JobTread
            if create_job_in_jobtread(jobtread_job_data):
                print("Job successfully created in JobTread.")
            else:
                print("Failed to create job in JobTread.")

        else:
            print("Warning: Unsupported event type.")

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"Exception in housecallpro_webhook: {e}")
        return jsonify({"status": "success", "message": str(e)}), 200

# Root route
@app.route("/")
def home():
    return "Integration Server is Running!"

# Run the Flask app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use Render's PORT variable
    app.run(host="0.0.0.0", port=port)
