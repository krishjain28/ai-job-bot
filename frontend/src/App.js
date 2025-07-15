import React, { useState, useEffect } from 'react';
import {
  Container,
  Box,
  Typography,
  AppBar,
  Toolbar,
  Grid,
  Paper,
  Button,
  CircularProgress,
  Alert,
  Snackbar
} from '@mui/material';
import {
  Work as WorkIcon,
  Send as SendIcon,
  Timeline as TimelineIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import axios from 'axios';
import StatsCard from './components/StatsCard';
import JobsList from './components/JobsList';
import ApplicationsList from './components/ApplicationsList';
import RunsList from './components/RunsList';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [stats, setStats] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [applications, setApplications] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

  const fetchData = async () => {
    try {
      setLoading(true);
      const [statsRes, jobsRes, applicationsRes, runsRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/stats`),
        axios.get(`${API_BASE_URL}/jobs?limit=10`),
        axios.get(`${API_BASE_URL}/applications?limit=10`),
        axios.get(`${API_BASE_URL}/runs?limit=5`)
      ]);

      setStats(statsRes.data);
      setJobs(jobsRes.data);
      setApplications(applicationsRes.data);
      setRuns(runsRes.data);
    } catch (err) {
      setError('Failed to fetch data from API');
      console.error('API Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const triggerJobRun = async () => {
    try {
      setRunning(true);
      await axios.post(`${API_BASE_URL}/run`);
      setSnackbar({
        open: true,
        message: 'Job run started successfully!',
        severity: 'success'
      });
      // Refresh data after a delay
      setTimeout(fetchData, 5000);
    } catch (err) {
      setSnackbar({
        open: true,
        message: 'Failed to start job run',
        severity: 'error'
      });
    } finally {
      setRunning(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <div className="App">
      <AppBar position="static">
        <Toolbar>
          <WorkIcon sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            AI Job Bot Dashboard
          </Typography>
          <Button
            color="inherit"
            startIcon={<RefreshIcon />}
            onClick={fetchData}
            disabled={loading}
          >
            Refresh
          </Button>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Stats Cards */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <StatsCard
              title="Total Jobs"
              value={stats?.total_jobs || 0}
              icon={<WorkIcon />}
              color="primary"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <StatsCard
              title="Applications Sent"
              value={stats?.total_applications || 0}
              icon={<SendIcon />}
              color="success"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <StatsCard
              title="Success Rate"
              value={`${stats?.success_rate?.toFixed(1) || 0}%`}
              icon={<TimelineIcon />}
              color="info"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <Button
                variant="contained"
                color="primary"
                size="large"
                startIcon={running ? <CircularProgress size={20} /> : <SendIcon />}
                onClick={triggerJobRun}
                disabled={running}
                fullWidth
              >
                {running ? 'Running...' : 'Start Job Run'}
              </Button>
            </Paper>
          </Grid>
        </Grid>

        {/* Main Content */}
        <Grid container spacing={3}>
          <Grid item xs={12} lg={8}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Recent Jobs
              </Typography>
              <JobsList jobs={jobs} />
            </Paper>
          </Grid>
          <Grid item xs={12} lg={4}>
            <Paper sx={{ p: 2, mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                Recent Applications
              </Typography>
              <ApplicationsList applications={applications} />
            </Paper>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Job Runs
              </Typography>
              <RunsList runs={runs} />
            </Paper>
          </Grid>
        </Grid>
      </Container>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </div>
  );
}

export default App; 