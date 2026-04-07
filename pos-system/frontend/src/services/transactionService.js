import api from './api';

export const transactionService = {
  // POST /api/transactions/
  createTransaction: async (transactionData) => {
    const response = await api.post('/transactions/', transactionData);
    return response.data;
  },

  // GET /api/transactions/
  getTransactions: async (params = {}) => {
    const response = await api.get('/transactions/', { params });
    return response.data;
  },

  // GET /api/transactions/{id}/
  getTransactionById: async (id) => {
    const response = await api.get(`/transactions/${id}/`);
    return response.data;
  },

  // POST /api/transactions/{id}/void/
  voidTransaction: async (id, reason) => {
    const response = await api.post(`/transactions/${id}/void/`, { reason });
    return response.data;
  },

  // POST /api/transactions/{id}/receipt/
  sendReceipt: async (id, email) => {
    const response = await api.post(`/transactions/${id}/receipt/`, { email });
    return response.data;
  },

  // GET /api/transactions/customer/{customerId}/
  getTransactionsByCustomer: async (customerId) => {
    const response = await api.get(`/transactions/customer/${customerId}/`);
    return response.data;
  },

  // GET /api/transactions/stats/today/
  getTodayStats: async () => {
    const response = await api.get('/transactions/stats/today/');
    return response.data;  // { sales, count }
  },

  // GET /api/transactions/range/?start=...&end=...
  getTransactionsByDateRange: async (start, end) => {
    const response = await api.get('/transactions/range/', { params: { start, end } });
    return response.data;
  },
};