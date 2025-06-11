// src/js/modules/cartManager.js

/**
 * МЕНЕДЖЕР КОРЗИНЫ С ПОДДЕРЖКОЙ ГОСТЕЙ
 * ====================================================
 * Основные улучшения:
 * - Шифрование данных корзины
 * - Валидация входных параметров
 * - Обработка ошибок при миграции
 * - Интеграция с системой аутентификации
 */

const CART_CONFIG = {
  STORAGE_PREFIX: 'guest_cart_',
  ENCRYPTION_KEY: 'your-32-byte-secure-key' // Заменить в продекшене
};

export class CartManager {
  constructor() {
    this.guestCart = [];
    this.sessionId = window.auth?.guestData?.id || null;
    this.loadGuestCart();
  }

  /**
   * ДОБАВЛЕНИЕ ТОВАРА В КОРЗИНУ ГОСТЯ
   * @param {string} productId - UUID товара
   * @param {number} quantity - Количество (1+)
   */
  addGuestItem(productId, quantity = 1) {
    try {
      this.validateItem(productId, quantity);
      
      const existing = this.guestCart.find(item => item.productId === productId);
      existing ? existing.quantity += quantity : this.guestCart.push({ productId, quantity });
      
      this.saveGuestCart();
    } catch (error) {
      console.error('Ошибка добавления товара:', error);
      throw error;
    }
  }

  /**
   * ЗАГРУЗКА КОРЗИНЫ ГОСТЯ
   */
  loadGuestCart() {
    try {
      const encryptedData = localStorage.getItem(this.getStorageKey());
      if (!encryptedData) return;
      
      const decrypted = this.decryptData(encryptedData);
      this.guestCart = JSON.parse(decrypted) || [];
    } catch (error) {
      console.error('Ошибка загрузки корзины:', error);
      this.guestCart = [];
    }
  }

  /**
   * МИГРАЦИЯ КОРЗИНЫ В АККАУНТ
   */
  async migrateToAccount(userId) {
    try {
      if (!this.guestCart.length) return;
      
      const response = await fetch('/api/migrate-cart', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify({
          userId,
          items: this.guestCart
        })
      });

      if (!response.ok) throw new Error('Migration failed');
      
      this.clearGuestCart();
      return true;
    } catch (error) {
      console.error('Ошибка миграции корзины:', error);
      return false;
    }
  }

  /** Приватные методы */
  validateItem(productId, quantity) {
    if (typeof productId !== 'string' || !productId.match(/^[a-f\d]{24}$/i)) {
      throw new Error('Неверный формат ID товара');
    }
    
    if (!Number.isInteger(quantity) || quantity < 1) {
      throw new Error('Некорректное количество');
    }
  }

  getStorageKey() {
    return `${CART_CONFIG.STORAGE_PREFIX}${this.sessionId}`;
  }

  async encryptData(data) {
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const encoder = new TextEncoder();
    
    const key = await crypto.subtle.importKey(
      'raw',
      new TextEncoder().encode(CART_CONFIG.ENCRYPTION_KEY),
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt', 'decrypt']
    );

    const encrypted = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv },
      key,
      encoder.encode(JSON.stringify(data))
    );
    
    return JSON.stringify({
      iv: Array.from(iv),
      data: Array.from(new Uint8Array(encrypted)),
      timestamp: Date.now()
    });
  }

  async decryptData(encryptedData) {
    try {
      const { iv, data, timestamp } = JSON.parse(encryptedData);
      
      const key = await crypto.subtle.importKey(
        'raw',
        new TextEncoder().encode(CART_CONFIG.ENCRYPTION_KEY),
        { name: 'AES-GCM', length: 256 },
        false,
        ['decrypt']
      );

      const decrypted = await crypto.subtle.decrypt(
        { name: 'AES-GCM', iv: new Uint8Array(iv) },
        key,
        new Uint8Array(data)
      );
      
      return new TextDecoder().decode(decrypted);
    } catch (error) {
      throw new Error('Не удалось расшифровать корзину');
    }
  }

  async saveGuestCart() {
    const encrypted = await this.encryptData(this.guestCart);
    localStorage.setItem(this.getStorageKey(), encrypted);
  }

  clearGuestCart() {
    this.guestCart = [];
    localStorage.removeItem(this.getStorageKey());
  }
}
