from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# API Keys & URLs from .env
JOBTREAD_API_KEY = os.getenv("JOBTREAD_API_KEY")
HOUSECALL_PRO_API_KEY = os.getenv("HOUSECALL_PRO_API_KEY")
JOBTREAD_API_URL = os.getenv("JOBTREAD_API_URL")
HOUSECALL_PRO_API_URL = os.getenv("HOUSECALL_PRO_API_URL")
ORGANIZATION_ID = os.getenv("ORGANIZATION_ID")

# Function to create a customer in JobTread
def create_customer_in_jobtread(customer_data):
    # Validate required fields
    if not customer_data.get("name"):
        print("Error: 'name' field is required for JobTread API.")
        return False

    query = {
        "query": {
            "$": {
                "grantKey": JOBTREAD_API_KEY,
            },
            "createAccount": {
                "$": {
                    "organizationId": ORGANIZATION_ID,
                    "name": customer_data.get("name"),  # Ensure this is not null
                    "type": "customer",
                },
                "createdAccount": {
                    "id": {},
                    "name": {},
                    "createdAt": {},
                    "type": {},
                    "organization": {
                        "id": {},
                        "name": {},
                    },
                },
            },
        }
    }
    
    headers = {"Content-Type": "application/json"}
    response = requests.post(JOBTREAD_API_URL, json=query, headers=headers)
    
    print("JobTread API Response:", response.status_code, response.text)
    return response.status_code == 200

# Function to create a customer in Housecall Pro
def create_customer_in_housecallpro(customer_data):
    url = f"{HOUSECALL_PRO_API_URL}/customers"
    headers = {
        "Authorization": f"Bearer {HOUSECALL_PRO_API_KEY}",
        "Content-Type": "application/json"
    }

    # Ensure at least one required field is present
    required_fields = ["first_name", "last_name", "email", "phone"]
    if not any(field in customer_data for field in required_fields):
        print("Error: Customer must have one of first name, last name, email, or phone number.")
        return False

    response = requests.post(url, json=customer_data, headers=headers)

    print("Housecall Pro API Response:", response.status_code, response.text)
    return response.status_code == 201

# Webhook endpoint for Housecall Pro
@app.route("/housecallpro-webhook", methods=["POST"])
def housecallpro_webhook():
    data = request.json
    print("Received data from Housecall Pro:", data)

    # Extract customer data from the nested structure
    customer = data.get("estimate", {}).get("customer", {})
    address = data.get("estimate", {}).get("address", {})

    # Prepare data for JobTread API
    jobtread_customer_data = {
        "name": customer.get("first_name", "") + " " + customer.get("last_name", ""),  # Combine first and last name
        "email": customer.get("email"),
        "phone": customer.get("mobile_number") or customer.get("home_number"),  # Use mobile or home number
        "industry": "Real Estate",
        "projectType": "Business Setup",
        "address": address.get("street")  # Include address if needed
    }

    # Validate required fields
    if not jobtread_customer_data.get("name"):
        print("Error: 'name' field is required for JobTread API.")
        return jsonify({"status": "error", "message": "'name' field is required"}), 400

    # Create customer in JobTread
    success = create_customer_in_jobtread(jobtread_customer_data)
    print("success", success)
    return jsonify({"status": "success" if success else "error"}), 200

# Webhook endpoint for JobTread
@app.route("/jobtread-webhook", methods=["POST"])
def jobtread_webhook():
    data = request.json
    print("Received data from JobTread:", data)

    # Extract customer data from the nested structure
    location = data.get("createdEvent", {}).get("location", {})
    contact = data.get("createdEvent", {}).get("contact", {})

    # Prepare data for Housecall Pro API
    housecallpro_customer_data = {
        "first_name": contact.get("firstName", ""),  # Use first name if available
        "last_name": contact.get("lastName", ""),    # Use last name if available
        "email": contact.get("email"),              # Use email if available
        "phone": contact.get("phone"),              # Use phone if available
        "address": location.get("address"),         # Include address if needed
        "industry": "Real Estate",
        "projectType": "Business Setup"
    }

    # Validate required fields
    required_fields = ["first_name", "last_name", "email", "phone"]
    if not any(field in housecallpro_customer_data for field in required_fields):
        print("Error: Customer must have one of first name, last name, email, or phone number.")
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    # Create customer in Housecall Pro
    success = create_customer_in_housecallpro(housecallpro_customer_data)
    print("success", success)
    return jsonify({"status": "success" if success else "error"}), 200

# Root route
@app.route("/")
def home():
    return "Integration Server is Running!"

# Run the Flask app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use Render's PORT variable
    app.run(host="0.0.0.0", port=port)