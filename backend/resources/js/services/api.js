import axios from 'axios';

const api = axios.create({
    baseURL: '/api',
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    },
});

export default {
    // Parameter validation
    validateParams(params) {
        return api.post('/params/validate', params);
    },

    // Jobs
    createJob(params) {
        return api.post('/jobs', params);
    },

    listJobs(limit = 20) {
        return api.get('/jobs', { params: { limit } });
    },

    getJob(id) {
        return api.get(`/jobs/${id}`);
    },

    deleteJob(id) {
        return api.delete(`/jobs/${id}`);
    },

    // Job actions
    startMesh(id) {
        return api.post(`/jobs/${id}/mesh`);
    },

    startSimulation(id) {
        return api.post(`/jobs/${id}/simulate`);
    },

    startRun(id) {
        return api.post(`/jobs/${id}/run`);
    },

    // Results
    getResultUrl(id, filename) {
        return `/api/jobs/${id}/results/${filename}`;
    },
};
