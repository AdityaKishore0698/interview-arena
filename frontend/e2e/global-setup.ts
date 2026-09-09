// global-setup.ts — runs once before all Playwright tests
// Flushes Redis to prevent cross-test matchmaking contamination

async function globalSetup() {
  try {
    // Call the backend Redis flush endpoint (or use the clear_redis.py approach via HTTP)
    const resp = await fetch('http://localhost:8000/api/v1/debug/flush-redis', { method: 'POST' })
      .catch(() => null);
    if (resp && resp.ok) {
      console.log('[global-setup] Redis flushed via debug endpoint.');
    } else {
      console.log('[global-setup] Debug flush endpoint not available; continuing with existing Redis state.');
    }
  } catch {
    console.log('[global-setup] Could not flush Redis; tests may have cross-test contamination.');
  }
}

export default globalSetup;
