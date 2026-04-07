import api from './api';

export const customerService = {
    getCustomers: async (params = {}) => {
        const response = await api.get('/customers/', { params });
        return response.data.results || response.data.content || response.data;
    },

    getCustomerById: async (id) => {
        const response = await api.get(`/customers/${id}/`);
        return response.data;
    },

    getCustomerByLoyalty: async (loyaltyNumber) => {
        const response = await api.get(`/customers/loyalty/${loyaltyNumber}/`);
        return response.data;
    },

    getCustomerByUserId: async (userId) => {
        const response = await api.get(`/customers/user/${userId}/`);
        return response.data;
    },

    createCustomer: async (customerData) => {
        const response = await api.post('/customers/', customerData);
        return response.data;
    },

    updateCustomer: async (id, customerData) => {
        const response = await api.put(`/customers/${id}/`, customerData);
        return response.data;
    },

    addPoints: async (id, points) => {
        const response = await api.post(`/customers/${id}/add-points/`, { points });
        return response.data;
    }
};
