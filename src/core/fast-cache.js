const redis = require('redis');
const client = redis.createClient({ url: 'redis://localhost:6379' });
client.on('error', () => {});

module.exports = {
  async get(key) {
    try { return await client.get(key); } catch { return null; }
  },
  async set(key, value, ttl = 3600) {
    try { await client.setEx(key, ttl, JSON.stringify(value)); } catch {}
  },
  async del(pattern) {
    try {
      const keys = await client.keys(pattern);
      if (keys.length) await client.del(keys);
    } catch {}
  }
};
