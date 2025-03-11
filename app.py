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

# Webhook endpoint for JobTread
@app.route("/jobtread-webhook", methods=["POST"])
def jobtread_webhook():
    try:
        data = request.json
        print("Received raw data from JobTread:", data)  # Log raw data

        if data is None:
            print("Error: No data received in the request.")
            return jsonify({"status": "error", "message": "No data received"}), 400

        # Check for 'createdEvent' key
        created_event = data.get("createdEvent", {})  # Default to empty dict if missing
        print("Created Event Data:", created_event)

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
                print("Warning: Unable to infer event type from the data.")
                event_type = "unknown"  # Default to unknown event type

        print("Processing Event Type:", event_type)

        # Handle the event based on its type
        if event_type == "fileCreated" or event_type == "fileUpdated":
            file_data = created_event.get("file", {})  # Default to empty dict if missing
            job = created_event.get("job", {})  # Default to empty dict if missing
            location = created_event.get("location", {})  # Default to empty dict if missing

            print("File Data:", file_data)
            print("Job Data:", job)
            print("Location Data:", location)

            # Add your logic here to handle the file event
            print(f"Handling {event_type} event for file: {file_data.get('name', 'Unknown')}")

            return jsonify({"status": "success"}), 200

        elif event_type == "customerCreated":
            # Handle customer creation event
            contact = created_event.get("contact", {})  # Default to empty dict if missing
            location = created_event.get("location", {})  # Default to empty dict if missing

            print("Contact Data:", contact)
            print("Location Data:", location)

            # Prepare data for Housecall Pro API (no validation for required fields)
            housecallpro_customer_data = {
                "name": contact.get("name", f"{contact.get('firstName', '')} {contact.get('lastName', '')}".strip()),
                "email": contact.get("email", ""),
                "phone": contact.get("phone", ""),
                "address": location.get("address", ""),
                "industry": "Real Estate",
                "projectType": "Business Setup"
            }

            print("Housecall Pro Customer Data:", housecallpro_customer_data)

            # Create customer in Housecall Pro (even if some fields are missing)
            success = create_customer_in_housecallpro(housecallpro_customer_data)
            print("Customer creation success:", success)
            return jsonify({"status": "success" if success else "error"}), 200

        elif event_type == "jobCreated":
            # Handle job creation event
            job = created_event.get("job", {})  # Default to empty dict if missing
            location = created_event.get("location", {})  # Default to empty dict if missing
            contact = created_event.get("contact", {})  # Default to empty dict if missing

            print("Job Data:", job)
            print("Location Data:", location)
            print("Contact Data:", contact)

            # Prepare data for Housecall Pro API (no validation for required fields)
            housecallpro_job_data = {
                "customer_id": contact.get("id", ""),  # Use the customer ID from JobTread (if available)
                "name": job.get("name", ""),
                "address": location.get("address", ""),
                "description": job.get("description", "")
            }

            print("Housecall Pro Job Data:", housecallpro_job_data)

            # Create job in Housecall Pro (even if some fields are missing)
            success = create_job_in_housecallpro(housecallpro_job_data)
            print("Job creation success:", success)
            return jsonify({"status": "success" if success else "error"}), 200

        elif event_type == "estimateCreated":
            # Handle estimate creation event
            estimate = created_event.get("estimate", {})  # Default to empty dict if missing
            job = created_event.get("job", {})  # Default to empty dict if missing
            contact = created_event.get("contact", {})  # Default to empty dict if missing

            print("Estimate Data:", estimate)
            print("Job Data:", job)
            print("Contact Data:", contact)

            # Prepare data for Housecall Pro API (no validation for required fields)
            housecallpro_estimate_data = {
                "customer_id": contact.get("id", ""),  # Use the customer ID from JobTread (if available)
                "job_id": job.get("id", ""),  # Use the job ID from JobTread (if available)
                "total_amount": estimate.get("totalAmount", 0),  # Default to 0 if missing
                "description": estimate.get("description", "")
            }

            print("Housecall Pro Estimate Data:", housecallpro_estimate_data)

            # Create estimate in Housecall Pro (even if some fields are missing)
            success = create_estimate_in_housecallpro(housecallpro_estimate_data)
            print("Estimate creation success:", success)
            return jsonify({"status": "success" if success else "error"}), 200

        else:
            print("Warning: Unsupported event type.")
            return jsonify({"status": "success", "message": "Unsupported event type, but request processed"}), 200

    except Exception as e:
        print(f"Exception in jobtread_webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Root route
@app.route("/")
def home():
    return "Integration Server is Running!"

# Run the Flask app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use Render's PORT variable
    app.run(host="0.0.0.0", port=port)
