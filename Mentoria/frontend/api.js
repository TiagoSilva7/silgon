(function () {
  // Alguns cenários comuns em dev:
  // - abrindo o HTML direto (file://)
  // - usando Live Server (porta 5500, etc.)
  // Nesses casos, um fetch('/api/...') tenta ir para o mesmo origin (file:// ou :5500)
  // e falha. Aqui, redirecionamos apenas rotas relativas /api/* para o backend local.

  const BACKEND_FALLBACK = 'http://localhost:3000';

  function shouldUseFallbackBase() {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    const port = window.location.port;

    if (protocol === 'file:') return true;

    const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';
    // Se estiver em localhost mas em outra porta (ex: Live Server), usar fallback
    if (isLocalhost && port && port !== '3000') return true;

    return false;
  }

  const API_BASE = shouldUseFallbackBase() ? BACKEND_FALLBACK : '';

  window.apiUrl = function apiUrl(path) {
    if (!API_BASE) return path;
    if (typeof path === 'string' && path.startsWith('/api/')) {
      return `${API_BASE}${path}`;
    }
    return path;
  };

  const originalFetch = window.fetch ? window.fetch.bind(window) : null;
  if (!originalFetch) return;

  window.fetch = function patchedFetch(input, init) {
    if (typeof input === 'string') {
      return originalFetch(window.apiUrl(input), init);
    }

    // Para Request/URL/etc, não alteramos (são absolutos na prática)
    return originalFetch(input, init);
  };
})();
