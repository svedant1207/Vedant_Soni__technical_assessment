import json
import secrets
import httpx
import os
from dotenv import load_dotenv
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
from urllib.parse import urlencode

from integrations.integration_item import IntegrationItem
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

# Load environment variables from a .env file in the project's root directory.
# This is used for securely managing credentials like client IDs and secrets.
load_dotenv()

# --- Configuration ---
# These variables are loaded from the .env file.
HUBSPOT_CLIENT_ID = os.environ.get('HUBSPOT_CLIENT_ID')
HUBSPOT_CLIENT_SECRET = os.environ.get('HUBSPOT_CLIENT_SECRET')
HUBSPOT_SCOPES = os.environ.get('HUBSPOT_SCOPES') # Defines the permissions our app is requesting
HUBSPOT_REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'

# HubSpot's standard API endpoints for authentication.
HUBSPOT_AUTH_URL = 'https://app.hubspot.com/oauth/authorize'
HUBSPOT_TOKEN_URL = 'https://api.hubapi.com/oauth/v1/token'
HUBSPOT_API_BASE_URL = 'https://api.hubapi.com'


# --- Part 1: OAuth Integration ---

async def authorize_hubspot(user_id, org_id):
    """
    Creates and returns the HubSpot authorization URL to initiate the OAuth 2.0 flow.
    This is the first step in the authentication process.
    """
    # A sanity check to ensure that the developer has set up their .env file correctly.
    if not HUBSPOT_CLIENT_ID or not HUBSPOT_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Missing HubSpot Client ID or Secret configuration.")

    # 1. Generate a cryptographically secure, random "state" string.
    # This is a crucial security measure to prevent Cross-Site Request Forgery (CSRF) attacks.
    state = secrets.token_urlsafe(32)
    state_data = {'state': state, 'user_id': user_id, 'org_id': org_id}
    encoded_state = json.dumps(state_data)

    # 2. Store this state in Redis with a 10-minute expiration. When HubSpot calls back,
    # we will check if the returned state matches this saved one.
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', encoded_state, expire=600)

    # 3. Construct the full authorization URL with the required query parameters.
    params = {
        "client_id": HUBSPOT_CLIENT_ID,
        "redirect_uri": HUBSPOT_REDIRECT_URI,
        "scope": HUBSPOT_SCOPES,
        "state": encoded_state,
    }
    auth_url = f"{HUBSPOT_AUTH_URL}?{urlencode(params)}"

    # 4. Return the complete URL. The frontend will open this URL in a new window,
    # prompting the user to log in and grant permissions.
    return auth_url


async def oauth2callback_hubspot(request: Request):
    """
    Handles the callback from HubSpot after the user has granted or denied permission.
    It exchanges the received authorization code for an access token.
    """
    # If the user denies the request, HubSpot adds an 'error' query parameter.
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.query_params.get('error_description'))

    # Extract the authorization code and the state from the callback URL's query parameters.
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')

    # Fix for a common issue where URL encoding can add '+' characters that break JSON parsing.
    cleaned_state = encoded_state.replace('+', '')
    state_data = json.loads(cleaned_state)

    # Extract our original state token and user identifiers.
    original_state_token = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')

    # --- SECURITY CHECK: Verify State ---
    # Retrieve the state we previously saved in Redis.
    saved_state_str = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')
    # If it doesn't exist or doesn't match what HubSpot sent back, abort the process.
    if not saved_state_str or original_state_token != json.loads(saved_state_str).get('state'):
        raise HTTPException(status_code=400, detail='State does not match. Possible CSRF attack.')

    # The state has served its purpose; delete it from Redis to prevent reuse.
    await delete_key_redis(f'hubspot_state:{org_id}:{user_id}')

    # --- Exchange Authorization Code for Access Token ---
    # Make a POST request to HubSpot's token endpoint to get the access and refresh tokens.
    async with httpx.AsyncClient() as client:
        response = await client.post(
            HUBSPOT_TOKEN_URL,
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': HUBSPOT_REDIRECT_URI,
                'client_id': HUBSPOT_CLIENT_ID,
                'client_secret': HUBSPOT_CLIENT_SECRET,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"Failed to fetch token: {response.text}")

    # --- Store Credentials in Redis ---
    # The token data is stored temporarily in Redis for the frontend to retrieve.
    await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(response.json()), expire=3600)

    # --- Close Browser Popup ---
    # Return a simple HTML response that executes a script to close the popup window.
    close_window_script = "<html><script>window.close();</script></html>"
    return HTMLResponse(content=close_window_script)


async def get_hubspot_credentials(user_id, org_id):
    """
    An endpoint for the frontend to securely retrieve the stored credentials
    immediately after the OAuth flow is complete.
    """
    credentials_str = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    if not credentials_str:
        raise HTTPException(status_code=404, detail='No HubSpot credentials found. Please authorize first.')

    # For security, delete the key after it's been retrieved to ensure it's used only once.
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')

    return json.loads(credentials_str)


# --- Part 2: Loading HubSpot Items ---

def create_integration_item_metadata_object(contact_json: dict) -> IntegrationItem:
    """
    A helper function that takes a raw JSON object for a HubSpot contact
    and maps its fields to our standardized `IntegrationItem` class structure.
    """
    properties = contact_json.get('properties', {})

    # Safely get contact properties, providing empty strings as defaults.
    first_name = properties.get('firstname', '')
    last_name = properties.get('lastname', '')
    full_name = f"{first_name} {last_name}".strip()
    # Use the full name if available, otherwise fall back to the email.
    name = full_name if full_name else properties.get('email', 'Unnamed Contact')

    # Create and return the standardized item.
    return IntegrationItem(
        id=contact_json.get('id'),
        type='contact',
        name=name,
        creation_time=contact_json.get('createdAt'),
        last_modified_time=contact_json.get('updatedAt'),
    )


async def get_items_hubspot(credentials: dict) -> list[IntegrationItem]:
    """
    Uses the provided OAuth credentials to fetch a list of contacts from the HubSpot API.
    """
    access_token = credentials.get('access_token')
    if not access_token:
        raise HTTPException(status_code=400, detail="Missing access_token in credentials.")

    # We can specify which properties we want the API to return to keep the response small.
    properties_to_fetch = "firstname,lastname,email"
    contacts_url = f"{HUBSPOT_API_BASE_URL}/crm/v3/objects/contacts?properties={properties_to_fetch}"

    headers = {'Authorization': f'Bearer {access_token}'}

    # Make the authenticated API request to HubSpot.
    async with httpx.AsyncClient() as client:
        response = await client.get(contacts_url, headers=headers)

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to fetch HubSpot contacts: {response.text}"
        )

    # Process the response: iterate through the contacts and map each one
    # to our standardized IntegrationItem format.
    list_of_integration_items = []
    results = response.json().get('results', [])
    for contact in results:
        list_of_integration_items.append(
            create_integration_item_metadata_object(contact)
        )

    # Print a success message to the console as requested by the assessment instructions.
    print(f"Successfully fetched {len(list_of_integration_items)} contacts from HubSpot.")
    return list_of_integration_items
