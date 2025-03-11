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
        print("Received data from JobTread:", data)

        # Debug: Check if data is None
        if data is None:
            print("Error: No data received in the request.")
            return jsonify({"status": "error", "message": "No data received"}), 400

        # Extract event type
        event_type = data.get("createdEvent", {}).get("type")

        # If event_type is None, infer it based on the data structure
        if event_type is None:
            if "contact" in data.get("createdEvent", {}):
                event_type = "customerCreated"
            elif "job" in data.get("createdEvent", {}):
                event_type = "jobCreated"
            elif "estimate" in data.get("createdEvent", {}):
                event_type = "estimateCreated"
            elif "file" in data.get("createdEvent", {}):
                event_type = "fileCreated"  # Infer fileCreated event
            else:
                print("Warning: Unable to infer event type from the data.")
                return jsonify({"status": "error", "message": "Unable to infer event type"}), 400

        print("Event Type:", event_type)

        if event_type == "customerCreated":
            # Handle new customer
            contact = data.get("createdEvent", {}).get("contact", {})
            location = data.get("createdEvent", {}).get("location", {})

            # Log contact and location data for debugging
            print("Contact Data:", contact)
            print("Location Data:", location)

            # Prepare data for Housecall Pro API
            housecallpro_customer_data = {
                "name": contact.get("name", f"{contact.get('firstName', '')} {contact.get('lastName', '')}".strip()),
                "email": contact.get("email"),
                "phone": contact.get("phone"),
                "address": location.get("address"),
                "industry": "Real Estate",
                "projectType": "Business Setup"
            }

            # Log prepared customer data for debugging
            print("Housecall Pro Customer Data:", housecallpro_customer_data)

            # Validate required fields
            required_fields = ["name", "email", "phone"]
            if not any(field in housecallpro_customer_data for field in required_fields):
                print("Error: Customer must have one of name, email, or phone number.")
                return jsonify({"status": "error", "message": "Missing required fields"}), 400

            # Create customer in Housecall Pro
            success = create_customer_in_housecallpro(housecallpro_customer_data)
            print("success", success)
            return jsonify({"status": "success" if success else "error"}), 200

        elif event_type == "jobCreated":
            # Handle new job
            job = data.get("createdEvent", {}).get("job", {})
            location = data.get("createdEvent", {}).get("location", {})
            contact = data.get("createdEvent", {}).get("contact", {})

            # Log job, location, and contact data for debugging
            print("Job Data:", job)
            print("Location Data:", location)
            print("Contact Data:", contact)

            # Prepare data for Housecall Pro API
            housecallpro_job_data = {
                "customer_id": contact.get("id"),  # Use the customer ID from JobTread
                "name": job.get("name"),
                "address": location.get("address"),
                "description": job.get("description")
            }

            # Log prepared job data for debugging
            print("Housecall Pro Job Data:", housecallpro_job_data)

            # Validate required fields
            required_fields = ["customer_id", "name", "address"]
            if not all(field in housecallpro_job_data for field in required_fields):
                print("Error: Missing required fields for creating a job.")
                return jsonify({"status": "error", "message": "Missing required fields"}), 400

            # Create job in Housecall Pro
            success = create_job_in_housecallpro(housecallpro_job_data)
            print("success", success)
            return jsonify({"status": "success" if success else "error"}), 200

        elif event_type == "estimateCreated":
            # Handle new estimate
            estimate = data.get("createdEvent", {}).get("estimate", {})
            job = data.get("createdEvent", {}).get("job", {})
            contact = data.get("createdEvent", {}).get("contact", {})

            # Log estimate, job, and contact data for debugging
            print("Estimate Data:", estimate)
            print("Job Data:", job)
            print("Contact Data:", contact)

            # Prepare data for Housecall Pro API
            housecallpro_estimate_data = {
                "customer_id": contact.get("id"),  # Use the customer ID from JobTread
                "job_id": job.get("id"),         # Use the job ID from JobTread
                "total_amount": estimate.get("totalAmount"),
                "description": estimate.get("description")
            }

            # Log prepared estimate data for debugging
            print("Housecall Pro Estimate Data:", housecallpro_estimate_data)

            # Validate required fields
            required_fields = ["customer_id", "job_id", "total_amount"]
            if not all(field in housecallpro_estimate_data for field in required_fields):
                print("Error: Missing required fields for creating an estimate.")
                return jsonify({"status": "error", "message": "Missing required fields"}), 400

            # Create estimate in Housecall Pro
            success = create_estimate_in_housecallpro(housecallpro_estimate_data)
            print("success", success)
            return jsonify({"status": "success" if success else "error"}), 200

        elif event_type == "fileCreated" or event_type == "fileUpdated":
            # Handle file created or updated event
            file_data = data.get("createdEvent", {}).get("file", {})
            job = data.get("createdEvent", {}).get("job", {})
            location = data.get("createdEvent", {}).get("location", {})

            # Log file, job, and location data for debugging
            print("File Data:", file_data)
            print("Job Data:", job)
            print("Location Data:", location)

            # Add your logic here to handle the file created or updated event
            # For example, you might want to log the file details or trigger another process
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
        print("Received data from Housecall Pro:", data)

        # Debug: Check if data is None
        if data is None:
            print("Error: No data received in the request.")
            return jsonify({"status": "error", "message": "No data received"}), 400

        # Extract event type
        event_type = data.get("event")
        print("Event Type:", event_type)

        if event_type == "job.updated":
            # Handle job updated event
            job_data = data.get("job", {})
            print("Processing updated job:", job_data)
            # Add your logic here to handle the updated job
            return jsonify({"status": "success"}), 200

        elif event_type == "estimate.updated":
            # Handle estimate updated event
            estimate_data = data.get("estimate", {})
            print("Processing updated estimate:", estimate_data)
            # Add your logic here to handle the updated estimate
            return jsonify({"status": "success"}), 200

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
