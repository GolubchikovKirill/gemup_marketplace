// src/js/modules/products.js

/**
 * СЕРВИС РАБОТЫ С ТОВАРАМИ И ОТЗЫВАМИ (v3.1)
 * ====================================================
 * Основные улучшения:
 * - Исправлены импорты зависимостей
 * - Добавлены отсутствующие методы
 * - Улучшена обработка ошибок
 * - Оптимизирована валидация данных
 */

import { CartManager } from './cartManager.js';

const PRODUCT_CONFIG = {
  API_BASE: 'https://api.yourdomain.com/v1',
  CACHE_TTL: 5 * 60 * 1000, // 5 минут
  VALIDATION: {
    REVIEW_MIN_LENGTH: 20,
    REVIEW_MAX_LENGTH: 1000
  }
};

export class ProductService {
  constructor() {
    this.cache = new Map();
    this.cartManager = new CartManager();
  }

  /**
   * ЗАГРУЗКА КАТАЛОГА С АВТОКЭШИРОВАНИЕМ
   */
  async loadCatalog() {
    const cacheKey = 'products';
    
    if (this.cache.has(cacheKey)) {
      const { data, timestamp } = this.cache.get(cacheKey);
      if (Date.now() - timestamp < PRODUCT_CONFIG.CACHE_TTL) return data;
    }

    try {
      const response = await fetch(`${PRODUCT_CONFIG.API_BASE}/products`);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      
      const data = await response.json();
      this.cache.set(cacheKey, { data, timestamp: Date.now() });
      
      return data;
    } catch (error) {
      this.handleError('Ошибка загрузки каталога', error);
      return [];
    }
  }

  /**
   * ДОБАВЛЕНИЕ ТОВАРА В КОРЗИНУ
   */
  async addToCart(productId, quantity = 1) {
    try {
      this.validateProductId(productId);
      
      if (window.auth?.isGuest()) {
        this.cartManager.addGuestItem(productId, quantity);
      } else {
        await this.sendCartRequest(productId, quantity);
      }
      
      this.updateStockDisplay(productId);
    } catch (error) {
      this.handleError('Ошибка добавления в корзину', error);
    }
  }

  /**
   * ОТПРАВКА ОТЗЫВА С ПРОВЕРКОЙ ПРАВ
   */
  async submitReview(productId, reviewData) {
    try {
      if (!(await this.checkPurchaseStatus(productId))) {
        throw new Error('REVIEW_NOT_ALLOWED');
      }

      const validation = this.validateReview(reviewData);
      if (!validation.valid) throw new Error(validation.errors);

      const response = await fetch(`${PRODUCT_CONFIG.API_BASE}/products/${productId}/reviews`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(reviewData)
      });

      return this.handleResponse(response);
    } catch (error) {
      this.handleError('Ошибка отправки отзыва', error);
      return false;
    }
  }

  /** Вспомогательные методы */
  async sendCartRequest(productId, quantity) {
    const response = await fetch(`${PRODUCT_CONFIG.API_BASE}/cart`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ productId, quantity })
    });
    return this.handleResponse(response);
  }

  validateProductId(productId) {
    if (!productId || typeof productId !== 'string') {
      throw new Error('Неверный идентификатор товара');
    }
  }

  async checkPurchaseStatus(productId) {
    try {
      const response = await fetch(`${PRODUCT_CONFIG.API_BASE}/purchases/${productId}`, {
        headers: this.getAuthHeaders()
      });
      return response.status === 200;
    } catch (error) {
      return false;
    }
  }

  getAuthHeaders() {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
      'X-CSRF-Token': window.auth?.getCSRFToken() || ''
    };
  }

  validateReview(reviewData) {
    const errors = [];
    
    if (!reviewData.text?.trim()) {
      errors.push('Текст отзыва обязателен');
    }
    
    if (reviewData.text.length < PRODUCT_CONFIG.VALIDATION.REVIEW_MIN_LENGTH) {
      errors.push(`Минимальная длина отзыва - ${PRODUCT_CONFIG.VALIDATION.REVIEW_MIN_LENGTH} символов`);
    }
    
    if (reviewData.text.length > PRODUCT_CONFIG.VALIDATION.REVIEW_MAX_LENGTH) {
      errors.push(`Максимальная длина отзыва - ${PRODUCT_CONFIG.VALIDATION.REVIEW_MAX_LENGTH} символов`);
    }
    
    return {
      valid: errors.length === 0,
      errors: errors.join(', ')
    };
  }

  async handleResponse(response) {
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Ошибка сервера');
    }
    return response.json();
  }

  updateStockDisplay(productId) {
    const productElement = document.querySelector(`[data-product-id="${productId}"]`);
    if (productElement) {
      const stockElement = productElement.querySelector('.itemsLeft span');
      const newStock = parseInt(stockElement.textContent) - 1;
      stockElement.textContent = newStock > 0 ? newStock : '0';
    }
  }

  handleError(context, error) {
    console.error(`${context}:`, error);
    if (typeof window.showSystemMessage === 'function') {
      window.showSystemMessage(`${context}: ${error.message}`, 'error');
    }
  }
}
