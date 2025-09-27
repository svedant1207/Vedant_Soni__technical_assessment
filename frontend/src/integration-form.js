import { useState } from 'react';
import {
    Box,
    Autocomplete,
    TextField,
} from '@mui/material';
import { AirtableIntegration } from './integrations/airtable';
import { NotionIntegration } from './integrations/notion';
import { HubSpotIntegration } from './integrations/hubspot';
import { DataForm } from './data-form';

/**
 * A mapping of integration names (displayed in the UI) to their corresponding React components.
 * This allows for dynamic rendering of the selected integration's UI.
 */
const integrationMapping = {
    'Notion': NotionIntegration,
    'Airtable': AirtableIntegration,
    'HubSpot': HubSpotIntegration,
};

/**
 * IntegrationForm Component
 * This is the main component for the integration page. It allows users to select
 * an integration type and then guides them through the connection and data loading process.
 */
export const IntegrationForm = () => {
    // --- State Management ---

    // `integrationParams` holds the credentials and type after a successful connection.
    const [integrationParams, setIntegrationParams] = useState({});
    // `user` and `org` are example identifiers passed to the backend during the OAuth flow.
    const [user, setUser] = useState('TestUser');
    const [org, setOrg] = useState('TestOrg');
    // `currType` stores the string name of the integration selected from the dropdown (e.g., 'HubSpot').
    const [currType, setCurrType] = useState(null);

    // `CurrIntegration` dynamically holds the component to be rendered based on the user's selection.
    const CurrIntegration = integrationMapping[currType];

  return (
    <Box display='flex' justifyContent='center' alignItems='center' flexDirection='column' sx={{ width: '100%' }}>
        <Box display='flex' flexDirection='column'>
        {/* Input fields for user and organization IDs. */}
        <TextField
            label="User"
            value={user}
            onChange={(e) => setUser(e.target.value)}
            sx={{mt: 2}}
        />
        <TextField
            label="Organization"
            value={org}
            onChange={(e) => setOrg(e.target.value)}
            sx={{mt: 2}}
        />
        {/* Autocomplete dropdown to select the desired integration. */}
        <Autocomplete
            id="integration-type"
            options={Object.keys(integrationMapping)}
            sx={{ width: 300, mt: 2 }}
            renderInput={(params) => <TextField {...params} label="Integration Type" />}
            onChange={(e, value) => setCurrType(value)}
        />
        </Box>

        {/* --- Conditional Rendering --- */}

        {/* The selected integration's connection component is only rendered if a type has been chosen. */}
        {currType &&
        <Box>
            <CurrIntegration user={user} org={org} integrationParams={integrationParams} setIntegrationParams={setIntegrationParams} />
        </Box>
        }

        {/* The DataForm for loading items is only rendered after credentials have been successfully obtained. */}
        {integrationParams?.credentials &&
        <Box sx={{mt: 2}}>
            <DataForm integrationType={integrationParams?.type} credentials={integrationParams?.credentials} />
        </Box>
        }
    </Box>
  );
}
