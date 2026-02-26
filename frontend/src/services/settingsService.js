import apiClient from './apiClient';

export const getSettings = async () => {
    const res = await apiClient.get('/settings');
    return res.data;
};

export const saveAWSCredentials = async (credentials) => {
    const res = await apiClient.post('/settings/aws-credentials', credentials);
    return res.data;
};

export const switchToMock = async () => {
    const res = await apiClient.post('/settings/use-mock');
    return res.data;
};
