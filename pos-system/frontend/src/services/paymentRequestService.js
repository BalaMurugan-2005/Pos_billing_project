import api from './api';

export const paymentRequestService = {
    // POST /api/payment-requests/
    createRequest: async (customerId, amount, method) => {
        const response = await api.post('/payment-requests/', {
            customerId,
            amount,
            method,
        });
        return response.data;
    },

    // GET /api/payment-requests/active/{customerId}/
    getActiveRequests: async (customerId) => {
        const response = await api.get(`/payment-requests/active/${customerId}/`);
        return response.data;
    },

    // POST /api/payment-requests/{requestId}/status/
    updateStatus: async (requestId, status) => {
        const response = await api.post(`/payment-requests/${requestId}/status/`, {
            status,
        });
        return response.data;
    },

    // GET /api/payment-requests/{requestId}/  — polls until COMPLETED or DECLINED
    waitForPayment: async (requestId) => {
        return new Promise((resolve, reject) => {
            const interval = setInterval(async () => {
                try {
                    const response = await api.get(`/payment-requests/${requestId}/`);
                    if (response.data.status === 'COMPLETED') {
                        clearInterval(interval);
                        resolve(response.data);
                    } else if (response.data.status === 'DECLINED') {
                        clearInterval(interval);
                        reject(new Error('Payment declined by customer'));
                    }
                } catch (e) {
                    // Keep polling unless explicit failure or timeout
                }
            }, 2000);

            // Auto-timeout after 5 minutes
            setTimeout(() => {
                clearInterval(interval);
                reject(new Error('Payment request timed out'));
            }, 300000);
        });
    },
};
