import React from 'react';
import { Paper, Box, Typography } from '@mui/material';

const StatsCard = ({ title, value, icon, color = 'primary' }) => {
  return (
    <Paper sx={{ p: 2, textAlign: 'center' }}>
      <Box display="flex" alignItems="center" justifyContent="center" mb={1}>
        <Box color={`${color}.main`} mr={1}>
          {icon}
        </Box>
        <Typography variant="h4" component="div" color={`${color}.main`}>
          {value}
        </Typography>
      </Box>
      <Typography variant="body2" color="text.secondary">
        {title}
      </Typography>
    </Paper>
  );
};

export default StatsCard; 