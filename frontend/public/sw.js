// Service worker do PWA (Parte 28) — cacheia SOMENTE assets estáticos do
// próprio domínio (js/css/imagens/fontes). Nunca intercepta: requisições
// que não sejam GET, de outra origem (API FastAPI, Supabase Auth), ou sob
// /api/ — nenhuma resposta autenticada, dado financeiro ou token passa
// por aqui. Sem modo offline financeiro: só os assets para a instalação
// na tela inicial funcionar bem.
const CACHE_NAME = "economia-uau-estatico-v1";
const EXTENSOES_CACHEAVEIS = [".js", ".css", ".png", ".jpg", ".jpeg", ".svg", ".woff", ".woff2", ".ico"];

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((chaves) => Promise.all(chaves.filter((c) => c !== CACHE_NAME).map((c) => caches.delete(c))))
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  if (event.request.method !== "GET" || url.origin !== self.location.origin) {
    return;
  }
  if (url.pathname.startsWith("/api/")) {
    return;
  }
  const ehAssetEstatico = EXTENSOES_CACHEAVEIS.some((ext) => url.pathname.endsWith(ext));
  if (!ehAssetEstatico) {
    return;
  }

  event.respondWith(
    caches.open(CACHE_NAME).then(async (cache) => {
      const cacheado = await cache.match(event.request);
      if (cacheado) return cacheado;
      const resposta = await fetch(event.request);
      if (resposta.ok) cache.put(event.request, resposta.clone());
      return resposta;
    })
  );
});
