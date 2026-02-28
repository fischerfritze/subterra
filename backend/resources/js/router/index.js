import { createRouter, createWebHistory } from 'vue-router';
import JobList from '@/views/JobList.vue';
import JobCreate from '@/views/JobCreate.vue';
import JobDetail from '@/views/JobDetail.vue';

const routes = [
    {
        path: '/',
        name: 'jobs',
        component: JobList,
    },
    {
        path: '/new',
        name: 'job-create',
        component: JobCreate,
    },
    {
        path: '/jobs/:id',
        name: 'job-detail',
        component: JobDetail,
        props: true,
    },
];

const router = createRouter({
    history: createWebHistory(),
    routes,
});

export default router;
