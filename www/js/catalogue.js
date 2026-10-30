const CACHE_TTL_MS = 5 * 60 * 1000;
const CACHE_LIMIT = 32;

export function createCatalogueLoader({
  fetchImpl = (...args) => fetch(...args),
  now = () => Date.now(),
  pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
} = {}) {
  const cache = new Map();
  const pending = new Map();

  async function requestJson(url) {
    for (let attempt = 0; ; attempt++) {
      try {
        const response = await fetchImpl(url, {
          cache: attempt === 0 ? "no-cache" : "reload",
        });
        if (!response.ok) {
          const error = new Error(
            `Failed to fetch ${response.url || url} (HTTP ${response.status})`
          );
          error.status = response.status;
          throw error;
        }
        return await response.json();
      } catch (error) {
        const transient =
          error instanceof TypeError ||
          (error.status >= 500 && error.status < 600);
        if (attempt > 0 || !transient) throw error;
        await pause(500);
      }
    }
  }

  return async (url) => {
    const cached = cache.get(url);
    let data;
    if (cached && cached.expires > now()) {
      data = cached.data;
    } else {
      cache.delete(url);
      if (!pending.has(url)) {
        const request = requestJson(url)
          .then((result) => {
            cache.set(url, { data: result, expires: now() + CACHE_TTL_MS });
            if (cache.size > CACHE_LIMIT)
              cache.delete(cache.keys().next().value);
            return result;
          })
          .finally(() => pending.delete(url));
        pending.set(url, request);
      }
      data = await pending.get(url);
    }
    // Normalization mutates JSON; each catalogue selection needs its own copy.
    return JSON.parse(JSON.stringify(data));
  };
}
