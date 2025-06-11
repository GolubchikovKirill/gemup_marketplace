// src/js/modules/auth.js

/**
 * МОДУЛЬ АУТЕНТИФИКАЦИИ С ПОДДЕРЖКОЙ ГОСТЕВЫХ СЕССИЙ
 * =================================================================
 * Основные функции:
 * - Управление сессиями пользователя и гостя
 * - Защита от CSRF-атак
 * - Автоматическая миграция данных гостя
 * - Интеграция с API
 */

const SECURITY_CONFIG = {
  API_BASE: 'https://api.yourdomain.com/v1',
  SESSION_STRATEGY: 'jwt',
  GUEST_ROLE: 'guest',
  TOKEN_REFRESH_INTERVAL: 300000 // 5 минут
};

export class AuthManager {
  constructor() {
    this.csrfToken = null;
    this.session = null;
    this.guestData = null;
    this.initialize();
  }

  /** 
   * ИНИЦИАЛИЗАЦИЯ СИСТЕМЫ
   */
  async initialize() {
    await this.loadCSRFToken();
    this.checkExistingSession();
    this.setupAutoRefresh();
  }

  /**
   * ЗАГРУЗКА CSRF-ТОКЕНА
   */
  async loadCSRFToken() {
    try {
      const response = await fetch(`${SECURITY_CONFIG.API_BASE}/csrf-token`, {
        credentials: 'include'
      });
      
      if (!response.ok) throw new Error('CSRF_FAILURE');
      
      this.csrfToken = response.headers.get('X-CSRF-Token');
      document.cookie = `csrf=${this.csrfToken}; Secure; SameSite=Strict`;
    } catch (error) {
      console.error('CSRF Error:', error);
      this.handleCriticalError('SECURITY_INIT_FAILED');
    }
  }

  /**
   * ПРОВЕРКА СУЩЕСТВУЮЩЕЙ СЕССИИ
   */
  checkExistingSession() {
    const token = localStorage.getItem('auth_token');
    if (token) {
      this.session = { token };
    } else {
      this.initGuestSession();
    }
  }

  /**
   * ИНИЦИАЛИЗАЦИЯ ГОСТЕВОЙ СЕССИИ
   */
  initGuestSession() {
    if (!localStorage.getItem('guestSession')) {
      const guestId = `guest_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('guestSession', JSON.stringify({
        id: guestId,
        role: SECURITY_CONFIG.GUEST_ROLE,
        cart: [],
        createdAt: new Date().toISOString()
      }));
    }
    this.guestData = JSON.parse(localStorage.getItem('guestSession'));
  }

  /**
   * ОБРАБОТКА ВХОДА
   */
  async handleLogin(credentials) {
    try {
      this.validateLoginData(credentials);
      
      const response = await fetch(`${SECURITY_CONFIG.API_BASE}/auth/login`, {
        method: 'POST',
        headers: this.getSecurityHeaders(),
        body: JSON.stringify(credentials)
      });

      if (!response.ok) throw new Error('LOGIN_FAILED');
      
      const data = await response.json();
      this.processSession(data);
      this.migrateGuestData();
    } catch (error) {
      this.handleAuthError(error);
    }
  }

  /**
   * ОБРАБОТКА РЕГИСТРАЦИИ
   */
  async handleRegistration(userData) {
    try {
      this.validateRegistrationData(userData);
      
      const response = await fetch(`${SECURITY_CONFIG.API_BASE}/auth/register`, {
        method: 'POST',
        headers: this.getSecurityHeaders(),
        body: JSON.stringify(userData)
      });

      if (!response.ok) throw new Error('REGISTRATION_FAILED');
      
      const data = await response.json();
      this.processSession(data);
      await this.migrateGuestData();
    } catch (error) {
      this.handleAuthError(error);
    }
  }

  /**
   * МИГРАЦИЯ ДАННЫХ ГОСТЯ
   */
  async migrateGuestData() {
    if (!this.guestData?.cart?.length) return;

    try {
      await fetch(`${SECURITY_CONFIG.API_BASE}/migrate`, {
        method: 'POST',
        headers: this.getSecurityHeaders(),
        body: JSON.stringify({
          guestId: this.guestData.id,
          cart: this.guestData.cart
        })
      });
      localStorage.removeItem('guestSession');
    } catch (error) {
      console.error('Migration error:', error);
    }
  }

  /**
   * ОБНОВЛЕНИЕ СЕССИИ
   */
  processSession(data) {
    localStorage.setItem('auth_token', data.accessToken);
    document.cookie = `refresh_token=${data.refreshToken}; Secure; HttpOnly`;
    this.session = data;
  }

  /**
   * ГЕНЕРАЦИЯ ЗАЩИЩЕННЫХ ЗАГОЛОВКОВ
   */
  getSecurityHeaders() {
    return {
      'Content-Type': 'application/json',
      'X-CSRF-Token': this.csrfToken,
      'X-Request-ID': crypto.randomUUID()
    };
  }

  /**
   * ВАЛИДАЦИЯ ДАННЫХ ВХОДА
   */
  validateLoginData({ login, password }) {
    if (!login || !password) throw new Error('EMPTY_FIELDS');
    if (password.length < 12) throw new Error('WEAK_PASSWORD');
  }

  /**
   * ОБРАБОТКА ОШИБОК
   */
  handleAuthError(error) {
    console.error('Auth error:', error.message);
    // Логика показа ошибок пользователю
  }

  /**
   * НАСТРОЙКА АВТООБНОВЛЕНИЯ
   */
  setupAutoRefresh() {
    setInterval(() => {
      if (this.session) this.loadCSRFToken();
    }, SECURITY_CONFIG.TOKEN_REFRESH_INTERVAL);
  }

  /**
   * ПРОВЕРКА СТАТУСА ГОСТЯ
   */
  isGuest() {
    return !this.session;
  }

  /**
   * ПОЛУЧЕНИЕ CSRF-ТОКЕНА
   */
  getCSRFToken() {
    return this.csrfToken;
  }
}
