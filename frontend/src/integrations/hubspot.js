// hubspot.js

import { useState, useEffect } from 'react';
import {
    Box,
    Button,
    CircularProgress
} from '@mui/material';
import axios from 'axios';

/**
 * HubSpotIntegration Component
 * * This component handles the entire user-facing flow for connecting a HubSpot account.
 * It follows a standard OAuth 2.0 pattern by opening a popup window for user authorization.
 * * @param {object} props - The component's props.
 * @param {string} props.user - The current user's ID.
 * @param {string} props.org - The current organization's ID.
 * @param {object} props.integrationParams - State object from the parent component.
 * @param {function} props.setIntegrationParams - Function to update the parent's state.
 */
export const HubSpotIntegration = ({ user, org, integrationParams, setIntegrationParams }) => {
    // --- State Management ---

    // `isConnected` tracks if we have successfully retrieved credentials for this session.
    const [isConnected, setIsConnected] = useState(false);
    // `isConnecting` is used to show a loading spinner and disable the button during the async OAuth flow.
    const [isConnecting, setIsConnecting] = useState(false);

    /**
     * Initiates the OAuth flow when the "Connect" button is clicked.
     */
    const handleConnectClick = async () => {
        try {
            // Set loading state to true
            setIsConnecting(true);

            // 1. Prepare the request body to send to our backend.
            const body = {
                user_id: user,
                org_id: org,
            };

            // 2. Request the unique HubSpot authorization URL from our backend server.
            const response = await axios.post(`http://localhost:8000/integrations/hubspot/authorize`, body);
            const authURL = response?.data;

            // Validate the response before opening the popup.
            if (!authURL || typeof authURL !== 'string') {
                setIsConnecting(false);
                alert('Could not get authorization URL from server.');
                return;
            }

            // 3. Open the HubSpot authorization page in a new popup window.
            const newWindow = window.open(authURL, 'HubSpot Authorization', 'width=600, height=600');

            // 4. Poll the popup window to detect when it has been closed by the user.
            // This is how we know the user has either completed or cancelled the authorization.
            const pollTimer = window.setInterval(() => {
                if (newWindow?.closed !== false) {
                    window.clearInterval(pollTimer);
                    // Once the window is closed, proceed to fetch the credentials.
                    handleWindowClosed();
                }
            }, 200);
        } catch (e) {
            setIsConnecting(false);
            // Display a user-friendly error message from the backend if available.
            alert(e?.response?.data?.detail || 'An error occurred during authorization.');
        }
    }

    /**
     * Fetches the stored credentials from the backend after the OAuth popup closes.
     */
    const handleWindowClosed = async () => {
        try {
            // 1. Prepare the request body.
            const body = {
                user_id: user,
                org_id: org,
            };

            // 2. Request the credentials from our backend. The backend would have received them
            // from HubSpot via the callback and stored them temporarily in Redis.
            const response = await axios.post(`http://localhost:8000/integrations/hubspot/credentials`, body);
            const credentials = response.data;

            // 3. If credentials are successfully retrieved, update the state.
            if (credentials) {
                setIsConnected(true);
                // Update the parent component's state to reflect the successful connection.
                setIntegrationParams(prev => ({ ...prev, credentials: credentials, type: 'HubSpot' }));
            }
            // Reset loading state
            setIsConnecting(false);
        } catch (e) {
            setIsConnecting(false);
            alert(e?.response?.data?.detail || 'Could not fetch credentials.');
        }
    }

    // This effect ensures the component's connection status is in sync with the parent state.
    // It's useful if the connection status is managed outside this component as well.
    useEffect(() => {
        setIsConnected(!!integrationParams?.credentials);
    }, [integrationParams]);

    return (
        <>
        <Box sx={{mt: 2}}>
            Parameters
            <Box display='flex' alignItems='center' justifyContent='center' sx={{mt: 2}}>
                <Button
                    variant='contained'
                    // The button's action depends on the connection state.
                    onClick={isConnected ? () => {} : handleConnectClick}
                    // The button's color indicates the connection status.
                    color={isConnected ? 'success' : 'primary'}
                    // Disable the button while the connection is in progress.
                    disabled={isConnecting}
                    style={{
                        pointerEvents: isConnected ? 'none' : 'auto',
                        cursor: isConnected ? 'default' : 'pointer',
                        opacity: isConnected ? 1 : undefined
                    }}
                >
                    {/* The button's text provides clear feedback to the user. */}
                    {isConnected ? 'HubSpot Connected' : isConnecting ? <CircularProgress size={20} /> : 'Connect to HubSpot'}
                </Button>
            </Box>
        </Box>
      </>
    );
}
