import React from 'react';
import {
  List,
  ListItem,
  ListItemText,
  Chip,
  Box,
  Typography,
  Link,
  Divider
} from '@mui/material';
import { format } from 'date-fns';

const JobsList = ({ jobs }) => {
  if (!jobs || jobs.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" align="center">
        No jobs found
      </Typography>
    );
  }

  return (
    <List>
      {jobs.map((job, index) => (
        <React.Fragment key={job.id}>
          <ListItem alignItems="flex-start">
            <ListItemText
              primary={
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="subtitle1" component="span">
                    {job.title}
                  </Typography>
                  {job.gpt_score && (
                    <Chip
                      label={`${job.gpt_score}/10`}
                      size="small"
                      color={job.gpt_score >= 8 ? 'success' : job.gpt_score >= 6 ? 'warning' : 'default'}
                    />
                  )}
                </Box>
              }
              secondary={
                <Box>
                  <Typography variant="body2" color="text.primary">
                    {job.company}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {job.location} • {job.salary || 'Salary not specified'}
                  </Typography>
                  {job.tags && job.tags.length > 0 && (
                    <Box mt={1}>
                      {job.tags.slice(0, 3).map((tag, tagIndex) => (
                        <Chip
                          key={tagIndex}
                          label={tag}
                          size="small"
                          variant="outlined"
                          sx={{ mr: 0.5, mb: 0.5 }}
                        />
                      ))}
                    </Box>
                  )}
                  <Box mt={1}>
                    <Link href={job.link} target="_blank" rel="noopener">
                      View Job
                    </Link>
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    Found: {format(new Date(job.created_at), 'MMM dd, yyyy')} • Source: {job.source}
                  </Typography>
                </Box>
              }
            />
          </ListItem>
          {index < jobs.length - 1 && <Divider />}
        </React.Fragment>
      ))}
    </List>
  );
};

export default JobsList; 