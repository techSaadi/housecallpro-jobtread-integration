from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# API Keys & URLs from .env
JOBTREAD_API_KEY = os.getenv("JOBTREAD_API_KEY")
HOUSECALL_PRO_API_KEY = os.getenv("HOUSECALL_PRO_API_KEY")
JOBTREAD_API_URL = os.getenv("JOBTREAD_API_URL")
HOUSECALL_PRO_API_URL = os.getenv("HOUSECALL_PRO_API_URL")
ORGANIZATION_ID = os.getenv("ORGANIZATION_ID")

# Event Handlers Dictionary
event_handlers = {}

def event_handler(event_type):
    """Decorator to register event handlers"""
    def wrapper(func):
        event_handlers[event_type] = func
        return func
    return wrapper

# Function to create a customer in JobTread
@event_handler("create_customer_jobtread")
def create_customer_in_jobtread(customer_data):
    if not customer_data.get("name"):
        print("Error: 'name' field is required for JobTread API.")
        return False
    
    query = {
        "query": {
            "$": {"grantKey": JOBTREAD_API_KEY},
            "createAccount": {
                "$": {"organizationId": ORGANIZATION_ID, "name": customer_data.get("name"), "type": "customer"},
                "createdAccount": {"id": {}, "name": {}, "createdAt": {}, "type": {}, "organization": {"id": {}, "name": {}}},
            },
        }
    }
    
    headers = {"Content-Type": "application/json"}
    response = requests.post(JOBTREAD_API_URL, json=query, headers=headers)
    print("JobTread API Response:", response.status_code, response.text)
    return response.status_code == 200

# Function to create a customer in Housecall Pro
@event_handler("create_customer_housecallpro")
def create_customer_in_housecallpro(customer_data):
    url = f"{HOUSECALL_PRO_API_URL}/customers"
    headers = {"Authorization": f"Bearer {HOUSECALL_PRO_API_KEY}", "Content-Type": "application/json"}
    
    if not any(field in customer_data for field in ["first_name", "last_name", "email", "phone"]):
        print("Error: Customer must have at least one required field.")
        return False
    
    response = requests.post(url, json=customer_data, headers=headers)
    print("Housecall Pro API Response:", response.status_code, response.text)
    return response.status_code == 201

# Generic Webhook Handler
def process_webhook(event_type, data):
    handler = event_handlers.get(event_type)
    if handler:
        return handler(data)
    print(f"Warning: No handler registered for event type '{event_type}'")
    return False

# Webhook endpoints
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    event_type = data.get("event_type")  # Expect event_type in payload
    print(f"Received Webhook: {event_type}")
    
    success = process_webhook(event_type, data)
    return jsonify({"status": "success" if success else "error"}), 200

@app.route("/")
def home():
    return "Integration Server is Running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)