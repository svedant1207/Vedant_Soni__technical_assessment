import { useState } from 'react';
import {
    Box,
    TextField,
    Button,
} from '@mui/material';
import axios from 'axios';

/**
 * A mapping of integration types to their corresponding backend endpoint slugs.
 * This allows the component to dynamically construct the correct API URL.
 */
const endpointMapping = {
    'Notion': 'notion',
    'Airtable': 'airtable',
    'HubSpot': 'hubspot',
};

/**
 * DataForm Component
 * This component appears after a successful integration connection. It provides a button
 * to load data from the connected service and a text field to display the results.
 * @param {object} props - The component's props.
 * @param {string} props.integrationType - The type of the currently connected integration (e.g., 'HubSpot').
 * @param {object} props.credentials - The authentication credentials retrieved from the OAuth flow.
 */
export const DataForm = ({ integrationType, credentials }) => {
    // State to hold the data fetched from the backend.
    const [loadedData, setLoadedData] = useState(null);
    // Determine the correct API endpoint based on the integration type.
    const endpoint = endpointMapping[integrationType];

    /**
     * Handles the "Load Data" button click.
     * It sends the credentials to the backend, which then uses them to fetch
     * data from the third-party service (e.g., HubSpot).
     */
    const handleLoad = async () => {
        try {
            // 1. Prepare the JSON body for the request.
            const body = {
                credentials: credentials
            };

            // 2. Make a POST request to the integration's specific 'load' endpoint.
            const response = await axios.post(`http://localhost:8000/integrations/${endpoint}/get_hubspot_items`, body);
            const data = response.data;

            // 3. Update the state with the fetched data.
            // We use JSON.stringify to format the object nicely for display in the TextField.
            setLoadedData(JSON.stringify(data, null, 2));
        } catch (e) {
            // Display an error message if the API call fails.
            alert(e?.response?.data?.detail);
        }
    }

    return (
        <Box display='flex' justifyContent='center' alignItems='center' flexDirection='column' width='100%'>
            <Box display='flex' flexDirection='column' width='100%'>
                {/* Text field to display the loaded data. It's disabled and multiline for readability. */}
                <TextField
                    label="Loaded Data"
                    value={loadedData || ''}
                    sx={{mt: 2}}
                    InputLabelProps={{ shrink: true }}
                    disabled
                    multiline
                    rows={10}
                />
                <Button
                    onClick={handleLoad}
                    sx={{mt: 2}}
                    variant='contained'
                >
                    Load Data
                </Button>
                {/* Button to clear the displayed data from the UI. */}
                <Button
                    onClick={() => setLoadedData(null)}
                    sx={{mt: 1}}
                    variant='contained'
                >
                    Clear Data
                </Button>
            </Box>
        </Box>
    );
}
