import api from './api';

export const productService = {
  getProducts: async (params = {}) => {
    const response = await api.get('/products/', { params });
    return response.data.results || response.data.content || response.data;
  },

  getProductByBarcode: async (barcode) => {
    const response = await api.get(`/products/barcode/${barcode}/`);
    return response.data;
  },

  getProductById: async (id) => {
    const response = await api.get(`/products/${id}/`);
    return response.data;
  },

  searchProducts: async (query) => {
    const response = await api.get('/products/', { params: { search: query } });
    return response.data.results || response.data;
  },

  createProduct: async (productData) => {
    const response = await api.post('/products/', productData);
    return response.data;
  },

  updateProduct: async (id, productData) => {
    const response = await api.put(`/products/${id}/`, productData);
    return response.data;
  },

  deleteProduct: async (id) => {
    const response = await api.delete(`/products/${id}/`);
    return response.data;
  },

  checkInventory: async (productId) => {
    const response = await api.get(`/products/${productId}/`);
    return response.data;
  },

  updateInventory: async (productId, quantity, type = 'adjustment', reason = 'Manual update') => {
    const response = await api.post('/inventory/', {
      product: productId,
      quantity_change: quantity,
      movement_type: type,
      reason: reason
    });
    return response.data;
  }
};