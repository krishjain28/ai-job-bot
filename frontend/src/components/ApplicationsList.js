import React from 'react';
import {
  List,
  ListItem,
  ListItemText,
  Chip,
  Box,
  Typography,
  Divider
} from '@mui/material';
import { format } from 'date-fns';

const ApplicationsList = ({ applications }) => {
  if (!applications || applications.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" align="center">
        No applications yet
      </Typography>
    );
  }

  const getStatusColor = (status) => {
    switch (status.toLowerCase()) {
      case 'applied':
        return 'success';
      case 'error':
        return 'error';
      case 'pending':
        return 'warning';
      default:
        return 'default';
    }
  };

  return (
    <List dense>
      {applications.map((app, index) => (
        <React.Fragment key={app.id}>
          <ListItem alignItems="flex-start">
            <ListItemText
              primary={
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2" component="span">
                    Application #{app.id.slice(-6)}
                  </Typography>
                  <Chip
                    label={app.status}
                    size="small"
                    color={getStatusColor(app.status)}
                  />
                </Box>
              }
              secondary={
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {format(new Date(app.timestamp), 'MMM dd, HH:mm')}
                  </Typography>
                  {app.message && (
                    <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                      "{app.message.substring(0, 50)}..."
                    </Typography>
                  )}
                  {app.response_received && (
                    <Chip
                      label="Response Received"
                      size="small"
                      color="success"
                      variant="outlined"
                      sx={{ mt: 0.5 }}
                    />
                  )}
                </Box>
              }
            />
          </ListItem>
          {index < applications.length - 1 && <Divider />}
        </React.Fragment>
      ))}
    </List>
  );
};

export default ApplicationsList; 