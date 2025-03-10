from flask import Flask, request, jsonify
import requests
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# API Keys & URLs from .env
JOBTREAD_API_KEY = os.getenv("JOBTREAD_API_KEY")
HOUSECALL_PRO_API_KEY = os.getenv("HOUSECALL_PRO_API_KEY")
JOBTREAD_API_URL = os.getenv("JOBTREAD_API_URL")
HOUSECALL_PRO_API_URL = os.getenv("HOUSECALL_PRO_API_URL")
ORGANIZATION_ID = os.getenv("ORGANIZATION_ID")

# Event Handlers Registry - organized by source and event type
event_handlers = {
    "jobtread": {},
    "housecallpro": {}
}

def register_handler(source, event_type):
    """Decorator to register a handler function for a specific source and event type"""
    def decorator(func):
        if source not in event_handlers:
            event_handlers[source] = {}
        event_handlers[source][event_type] = func
        logger.info(f"Registered handler for {source} event: {event_type}")
        return func
    return decorator

# JobTread API Helper Functions
def create_customer_in_jobtread(customer_data):
    """Create a customer in JobTread"""
    if not customer_data.get("name"):
        logger.error("Error: 'name' field is required for JobTread API.")
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
    
    # Add additional customer fields if available
    if customer_data.get("email"):
        query["query"]["createAccount"]["$"]["email"] = customer_data.get("email")
    if customer_data.get("phone"):
        query["query"]["createAccount"]["$"]["phoneNumber"] = customer_data.get("phone")
    
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(JOBTREAD_API_URL, json=query, headers=headers)
        logger.info(f"JobTread API Response: {response.status_code}")
        if response.status_code == 200:
            return response.json()
        return False
    except Exception as e:
        logger.error(f"Error calling JobTread API: {str(e)}")
        return False

def create_job_in_jobtread(job_data):
    """Create a job in JobTread"""
    if not job_data.get("name") or not job_data.get("accountId"):
        logger.error("Error: 'name' and 'accountId' fields are required for JobTread job creation.")
        return False
        
    query = {
        "query": {
            "$": {"grantKey": JOBTREAD_API_KEY},
            "createJob": {
                "$": {
                    "organizationId": ORGANIZATION_ID, 
                    "name": job_data.get("name"),
                    "accountId": job_data.get("accountId")
                },
                "createdJob": {"id": {}, "name": {}, "createdAt": {}},
            },
        }
    }
    
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(JOBTREAD_API_URL, json=query, headers=headers)
        logger.info(f"JobTread Job Creation Response: {response.status_code}")
        if response.status_code == 200:
            return response.json()
        return False
    except Exception as e:
        logger.error(f"Error creating job in JobTread: {str(e)}")
        return False

# Housecall Pro API Helper Functions
def create_customer_in_housecallpro(customer_data):
    """Create a customer in Housecall Pro"""
    url = f"{HOUSECALL_PRO_API_URL}/customers"
    headers = {"Authorization": f"Bearer {HOUSECALL_PRO_API_KEY}", "Content-Type": "application/json"}
    
    # Format the data according to Housecall Pro requirements
    hcp_customer = {}
    
    # Required fields check
    if "name" in customer_data:
        # Split the name into first and last name
        name_parts = customer_data["name"].split(" ", 1)
        hcp_customer["first_name"] = name_parts[0]
        hcp_customer["last_name"] = name_parts[1] if len(name_parts) > 1 else ""
    else:
        hcp_customer["first_name"] = customer_data.get("first_name", "")
        hcp_customer["last_name"] = customer_data.get("last_name", "")
    
    hcp_customer["email"] = customer_data.get("email", "")
    hcp_customer["phone"] = customer_data.get("phone", "")
    
    if not any([hcp_customer["first_name"], hcp_customer["last_name"], hcp_customer["email"], hcp_customer["phone"]]):
        logger.error("Error: Customer must have at least one required field.")
        return False
        
    try:
        response = requests.post(url, json=hcp_customer, headers=headers)
        logger.info(f"Housecall Pro API Response: {response.status_code}")
        if response.status_code == 201:
            return response.json()
        return False
    except Exception as e:
        logger.error(f"Error calling Housecall Pro API: {str(e)}")
        return False

def create_job_in_housecallpro(job_data):
    """Create a job/estimate in Housecall Pro"""
    url = f"{HOUSECALL_PRO_API_URL}/estimates"
    headers = {"Authorization": f"Bearer {HOUSECALL_PRO_API_KEY}", "Content-Type": "application/json"}
    
    if not job_data.get("customer_id"):
        logger.error("Error: 'customer_id' is required for Housecall Pro estimate creation.")
        return False
        
    hcp_job = {
        "customer_id": job_data.get("customer_id"),
        "description": job_data.get("name", "New Job"),
        "line_items": []
    }
    
    try:
        response = requests.post(url, json=hcp_job, headers=headers)
        logger.info(f"Housecall Pro Estimate Creation Response: {response.status_code}")
        if response.status_code == 201:
            return response.json()
        return False
    except Exception as e:
        logger.error(f"Error creating estimate in Housecall Pro: {str(e)}")
        return False

# Register JobTread event handlers
@register_handler("jobtread", "accountCreated")
def handle_jobtread_account_created(event_data):
    """Handle JobTread account created event - sync to Housecall Pro"""
    logger.info("Processing JobTread account creation")
    
    # Extract customer data from JobTread event
    account = event_data.get("data", {}).get("next", {})
    if account and account.get("type") == "customer":
        customer_data = {
            "name": account.get("name", ""),
            "email": account.get("email", ""),
            "phone": account.get("phoneNumber", "")
        }
        
        # Create customer in Housecall Pro
        result = create_customer_in_housecallpro(customer_data)
        if result:
            logger.info(f"Successfully created customer in Housecall Pro: {result}")
            return True
    
    return False

@register_handler("jobtread", "jobCreated")
def handle_jobtread_job_created(event_data):
    """Handle JobTread job created event - sync to Housecall Pro"""
    logger.info("Processing JobTread job creation")
    
    # Extract job data from JobTread event
    job = event_data.get("data", {}).get("next", {})
    if job:
        # First, we need to find the customer ID in Housecall Pro
        # This would require maintaining a mapping between JobTread and Housecall Pro IDs
        # For now, we'll assume a simple mapping process
        account_id = job.get("accountId")
        
        # In a real implementation, you would query Housecall Pro to find the customer
        # For this example, we'll mock it with a placeholder
        housecall_customer_id = "hcp_customer_id_placeholder"  # This would come from your mapping logic
        
        job_data = {
            "customer_id": housecall_customer_id,
            "name": job.get("name", "New Job")
        }
        
        # Create job in Housecall Pro
        result = create_job_in_housecallpro(job_data)
        if result:
            logger.info(f"Successfully created job in Housecall Pro: {result}")
            return True
    
    return False

@register_handler("jobtread", "commentCreated")
def handle_jobtread_comment_created(event_data):
    """Handle JobTread comment created event"""
    logger.info("Processing JobTread comment creation")
    
    # Extract comment data
    comment_data = event_data.get("data", {}).get("next", {})
    if comment_data:
        logger.info(f"New comment on {comment_data.get('targetType')}: {comment_data.get('message')}")
        # You would implement syncing logic to Housecall Pro here
        # This depends on how comments map between the two systems
        return True
    
    return False

# Register Housecall Pro event handlers
@register_handler("housecallpro", "customer.created")
def handle_housecallpro_customer_created(event_data):
    """Handle Housecall Pro customer created event - sync to JobTread"""
    logger.info("Processing Housecall Pro customer creation")
    
    # Extract customer data from Housecall Pro event
    customer = event_data.get("data", {})
    if customer:
        # Format data for JobTread
        customer_data = {
            "name": f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip(),
            "email": customer.get("email", ""),
            "phone": customer.get("phone", "")
        }
        
        # Create customer in JobTread
        result = create_customer_in_jobtread(customer_data)
        if result:
            logger.info(f"Successfully created customer in JobTread: {result}")
            return True
    
    return False

@register_handler("housecallpro", "estimate.created")
def handle_housecallpro_estimate_created(event_data):
    """Handle Housecall Pro estimate created event - sync to JobTread"""
    logger.info("Processing Housecall Pro estimate creation")
    
    # Extract estimate data from Housecall Pro event
    estimate = event_data.get("data", {})
    if estimate:
        # First, we need to find the customer ID in JobTread
        # This would require maintaining a mapping between Housecall Pro and JobTread IDs
        # For now, we'll assume a simple mapping process
        customer_id = estimate.get("customer_id")
        
        # In a real implementation, you would query JobTread to find the account
        # For this example, we'll mock it with a placeholder
        jobtread_account_id = "jt_account_id_placeholder"  # This would come from your mapping logic
        
        job_data = {
            "name": estimate.get("description", "New Estimate"),
            "accountId": jobtread_account_id
        }
        
        # Create job in JobTread
        result = create_job_in_jobtread(job_data)
        if result:
            logger.info(f"Successfully created job in JobTread: {result}")
            return True
    
    return False

# Process webhook based on source and event type
def process_webhook(source, event_data):
    """Process a webhook from a specific source"""
    # Extract event type based on the source format
    event_type = None
    
    if source == "jobtread":
        event_type = event_data.get("type")
    elif source == "housecallpro":
        event_type = event_data.get("event")
    
    logger.info(f"Processing {source} webhook with event type: {event_type}")
    
    if not event_type:
        logger.warning(f"No event type found in {source} webhook data")
        return False
        
    # Look up the appropriate handler
    handler = event_handlers.get(source, {}).get(event_type)
    if handler:
        return handler(event_data)
    else:
        logger.warning(f"No handler registered for {source} event type '{event_type}'")
        return False

# Webhook endpoints
@app.route("/webhook/<source>", methods=["POST"])
def generic_webhook(source):
    """Generic webhook endpoint that routes to specific sources"""
    if source not in event_handlers:
        return jsonify({"status": "error", "message": f"Unknown source: {source}"}), 404
    
    data = request.json
    logger.info(f"Received {source} webhook: {data}")
    
    success = process_webhook(source, data)
    return jsonify({"status": "success" if success else "error"}), 200

@app.route("/jobtread-webhook", methods=["POST"])
def jobtread_webhook():
    """JobTread specific webhook endpoint"""
    data = request.json
    logger.info(f"Received JobTread webhook: {data}")
    
    success = process_webhook("jobtread", data)
    return jsonify({"status": "success" if success else "error"}), 200

@app.route("/housecallpro-webhook", methods=["POST"])
def housecallpro_webhook():
    """Housecall Pro specific webhook endpoint"""
    data = request.json
    logger.info(f"Received Housecall Pro webhook: {data}")
    
    success = process_webhook("housecallpro", data)
    return jsonify({"status": "success" if success else "error"}), 200

@app.route("/")
def home():
    """Home page showing available endpoints"""
    return jsonify({
        "status": "running",
        "endpoints": {
            "/webhook/jobtread": "JobTread webhook endpoint",
            "/webhook/housecallpro": "Housecall Pro webhook endpoint",
            "/jobtread-webhook": "Legacy JobTread webhook endpoint",
            "/housecallpro-webhook": "Legacy Housecall Pro webhook endpoint"
        },
        "registered_handlers": {
            source: list(handlers.keys()) 
            for source, handlers in event_handlers.items()
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting integration server on port {port}")
    app.run(host="0.0.0.0", port=port)