from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json

# Import integration-specific functions
from integrations.airtable import authorize_airtable, get_items_airtable, oauth2callback_airtable, get_airtable_credentials
from integrations.notion import authorize_notion, get_items_notion, oauth2callback_notion, get_notion_credentials
from integrations.hubspot import authorize_hubspot, get_hubspot_credentials, get_items_hubspot, oauth2callback_hubspot

app = FastAPI()

# --- Pydantic Models for Request Body Validation ---

# Defines the expected JSON structure for authorization and credential requests.
class AuthBody(BaseModel):
    user_id: str
    org_id: str

# Defines the expected JSON structure for data loading requests.
class LoadBody(BaseModel):
    credentials: dict

# --- CORS (Cross-Origin Resource Sharing) Configuration ---

# List of origins that are allowed to make requests to this backend.
origins = [
    "http://localhost:3000",  # The address of the React frontend app
]

# Add the CORS middleware to the application.
# This is crucial for allowing the frontend (on port 3000) to communicate
# with this backend (on port 8000) without being blocked by browser security policies.
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all request headers
)

@app.get('/')
def read_root():
    return {'Ping': 'Pong'}


# --- Airtable Endpoints ---
# These endpoints are configured to accept JSON payloads for consistency.
@app.post('/integrations/airtable/authorize')
async def authorize_airtable_integration(body: AuthBody):
    return await authorize_airtable(body.user_id, body.org_id)

@app.get('/integrations/airtable/oauth2callback')
async def oauth2callback_airtable_integration(request: Request):
    return await oauth2callback_airtable(request)

@app.post('/integrations/airtable/credentials')
async def get_airtable_credentials_integration(body: AuthBody):
    return await get_airtable_credentials(body.user_id, body.org_id)

@app.post('/integrations/airtable/load')
async def get_airtable_items(body: LoadBody):
    # The underlying airtable function expects a string, so we convert the dict back to a JSON string.
    return await get_items_airtable(json.dumps(body.credentials))


# --- Notion Endpoints ---
# These endpoints are also configured to accept JSON payloads.
@app.post('/integrations/notion/authorize')
async def authorize_notion_integration(body: AuthBody):
    return await authorize_notion(body.user_id, body.org_id)

@app.get('/integrations/notion/oauth2callback')
async def oauth2callback_notion_integration(request: Request):
    return await oauth2callback_notion(request)

@app.post('/integrations/notion/credentials')
async def get_notion_credentials_integration(body: AuthBody):
    return await get_notion_credentials(body.user_id, body.org_id)

@app.post('/integrations/notion/load')
async def get_notion_items(body: LoadBody):
    # The underlying notion function expects a string, so we convert the dict back to a JSON string.
    return await get_items_notion(json.dumps(body.credentials))

# --- HubSpot Endpoints ---
# These endpoints are what the HubSpot frontend component interacts with.

@app.post('/integrations/hubspot/authorize')
async def authorize_hubspot_integration(body: AuthBody):
    """
    Receives user and org IDs from the frontend and returns a unique
    HubSpot authorization URL to initiate the OAuth flow.
    """
    return await authorize_hubspot(body.user_id, body.org_id)

@app.get('/integrations/hubspot/oauth2callback')
async def oauth2callback_hubspot_integration(request: Request):
    """
    The redirect URI that HubSpot calls after the user grants permission.
    This endpoint is not called directly by our frontend. It handles the
    code-for-token exchange and stores the credentials.
    """
    return await oauth2callback_hubspot(request)

@app.post('/integrations/hubspot/credentials')
async def get_hubspot_credentials_integration(body: AuthBody):
    """
    Called by the frontend after the HubSpot popup window closes. This endpoint
    retrieves the temporarily stored credentials from Redis and sends them
    to the frontend.
    """
    return await get_hubspot_credentials(body.user_id, body.org_id)

@app.post('/integrations/hubspot/get_hubspot_items')
async def load_hubspot_items_integration(body: LoadBody):
    """
    Receives credentials from the frontend and uses them to fetch the list of
    contacts from the HubSpot API, returning them as a list of IntegrationItem objects.
    """
    return await get_items_hubspot(body.credentials)
