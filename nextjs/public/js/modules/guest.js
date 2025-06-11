// src/js/modules/guest.js

/**
 * МЕНЕДЖЕР ГОСТЕВЫХ СЕССИЙ (v2.0)
 * =================================================================
 * Основные улучшения:
 * 1. Шифрование данных AES-256-GCM
 * 2. Хеширование ID сессии
 * 3. Автоматическая очистка старых сессий
 * 4. Проверка целостности данных
 * 5. Полная интеграция с AuthManager
 */

const GUEST_CONFIG = {
  SESSION_PREFIX: 'gst_',
  DATA_TTL: 7 * 24 * 60 * 60 * 1000, // 1 неделя
  ENCRYPTION_KEY: 'your-32-byte-encryption-key' // Заменить в продакшене
};

class GuestSessionManager {
  constructor() {
    this.sessionId = null;
    this.cryptoKey = null;
    this.initialize();
  }

  /**
   * ИНИЦИАЛИЗАЦИЯ СЕССИИ
   * 1. Проверка существующей сессии
   * 2. Генерация новых ключей
   * 3. Очистка устаревших данных
   */
  async initialize() {
    await this.cleanupExpiredSessions();
    const existingSession = localStorage.getItem('guestSession');
    
    if (existingSession) {
      this.sessionId = this.validateSession(existingSession);
    } else {
      this.sessionId = this.generateSessionId();
      localStorage.setItem('guestSession', this.sessionId);
    }
    
    await this.initCryptoKey();
  }

  /**
   * ГЕНЕРАЦИЯ БЕЗОПАСНОГО ID СЕССИИ
   */
  generateSessionId() {
    const rawId = `${GUEST_CONFIG.SESSION_PREFIX}${Date.now()}_${crypto.getRandomValues(new Uint32Array(3)).join('-')}`;
    return this.hashData(rawId);
  }

  /**
   * СОХРАНЕНИЕ ДАННЫХ КОРЗИНЫ С ШИФРОВАНИЕМ
   */
  async saveCartData(items) {
    try {
      const encrypted = await this.encryptData(items);
      localStorage.setItem(this.getStorageKey('cart'), encrypted);
    } catch (error) {
      console.error('Ошибка сохранения корзины:', error);
      throw new Error('SAVE_FAILED');
    }
  }

  /**
   * ЗАГРУЗКА ДАННЫХ КОРЗИНЫ С ПРОВЕРКОЙ ЦЕЛОСТНОСТИ
   */
  async loadCartData() {
    try {
      const data = localStorage.getItem(this.getStorageKey('cart'));
      if (!data) return [];
      
      return await this.decryptData(data);
    } catch (error) {
      console.error('Ошибка загрузки корзины:', error);
      this.destroySession();
      return [];
    }
  }

  /**
   * МИГРАЦИЯ ДАННЫХ В АККАУНТ
   */
  async migrateToAccount(userId) {
    const cart = await this.loadCartData();
    const response = await fetch('/api/migrate-guest-data', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('authToken')}`
      },
      body: JSON.stringify({
        userId,
        guestSession: this.sessionId,
        cartData: cart
      })
    });
    
    if (response.ok) this.destroySession();
  }

  /**
   * УНИЧТОЖЕНИЕ СЕССИИ С ОЧИСТКОЙ ДАННЫХ
   */
  destroySession() {
    const keysToRemove = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key.startsWith(GUEST_CONFIG.SESSION_PREFIX)) {
        keysToRemove.push(key);
      }
    }
    
    keysToRemove.forEach(key => localStorage.removeItem(key));
    this.sessionId = null;
  }

  /** Приватные методы */
  async initCryptoKey() {
    this.cryptoKey = await crypto.subtle.importKey(
      'raw',
      new TextEncoder().encode(GUEST_CONFIG.ENCRYPTION_KEY),
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt', 'decrypt']
    );
  }

  async encryptData(data) {
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const encoder = new TextEncoder();
    
    const encrypted = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv },
      this.cryptoKey,
      encoder.encode(JSON.stringify(data))
    );
    
    return JSON.stringify({
      iv: Array.from(iv),
      data: Array.from(new Uint8Array(encrypted)),
      timestamp: Date.now()
    });
  }

  async decryptData(encryptedData) {
    const { iv, data, timestamp } = JSON.parse(encryptedData);
    
    if (Date.now() - timestamp > GUEST_CONFIG.DATA_TTL) {
      throw new Error('DATA_EXPIRED');
    }
    
    const decrypted = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: new Uint8Array(iv) },
      this.cryptoKey,
      new Uint8Array(data)
    );
    
    return JSON.parse(new TextDecoder().decode(decrypted));
  }

  hashData(data) {
    return crypto.subtle.digest('SHA-256', new TextEncoder().encode(data))
      .then(hash => {
        const hashArray = Array.from(new Uint8Array(hash));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
      });
  }

  getStorageKey(type) {
    return `${GUEST_CONFIG.SESSION_PREFIX}${this.sessionId}_${type}`;
  }

  async cleanupExpiredSessions() {
    const now = Date.now();
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key.startsWith(GUEST_CONFIG.SESSION_PREFIX) && key.includes('_cart')) {
        try {
          const data = JSON.parse(localStorage.getItem(key));
          if (now - data.timestamp > GUEST_CONFIG.DATA_TTL) {
            localStorage.removeItem(key);
          }
        } catch (e) {
          localStorage.removeItem(key);
        }
      }
    }
  }
}

// Инициализация глобального экземпляра
const guestSession = new GuestSessionManager();

// Интеграция с AuthManager
window.AuthManager.onRegister(user => guestSession.migrateToAccount(user.id));
window.AuthManager.onLogin(() => guestSession.destroySession());
