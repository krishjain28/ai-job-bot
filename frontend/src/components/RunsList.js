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

const RunsList = ({ runs }) => {
  if (!runs || runs.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" align="center">
        No runs yet
      </Typography>
    );
  }

  const getStatusColor = (status) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'success';
      case 'running':
        return 'info';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <List dense>
      {runs.map((run, index) => (
        <React.Fragment key={run.id}>
          <ListItem alignItems="flex-start">
            <ListItemText
              primary={
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2" component="span">
                    Run #{run.id.slice(-6)}
                  </Typography>
                  <Chip
                    label={run.status}
                    size="small"
                    color={getStatusColor(run.status)}
                  />
                </Box>
              }
              secondary={
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {format(new Date(run.start_time), 'MMM dd, HH:mm')}
                  </Typography>
                  <Box mt={0.5}>
                    <Typography variant="caption" display="block">
                      Found: {run.jobs_found} • Filtered: {run.jobs_filtered} • Applied: {run.applications_sent}
                    </Typography>
                  </Box>
                  {run.errors && run.errors.length > 0 && (
                    <Typography variant="caption" color="error" display="block">
                      {run.errors.length} error(s)
                    </Typography>
                  )}
                </Box>
              }
            />
          </ListItem>
          {index < runs.length - 1 && <Divider />}
        </React.Fragment>
      ))}
    </List>
  );
};

export default RunsList; 