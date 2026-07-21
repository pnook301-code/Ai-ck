module.exports = {
  apps: [
    // CK-NEXUS Main Gateway
    {
      name: 'ck-nexus',
      script: 'server.js',
      cwd: '/workspace/ck-nexus',
      env: {
        NODE_ENV: 'production',
        PORT: 3000,
        OPENCODE_SERVER_PASSWORD: 'ck-nexus-2026-secure'
      },
      autorestart: true,
      watch: false,
      max_restarts: 10,
      min_uptime: '10s'
    },
    // n8n Workflow Engine
    {
      name: 'n8n',
      script: 'n8n',
      args: 'start',
      env: {
        N8N_HOST: '0.0.0.0',
        N8N_PORT: 5678,
        N8N_BASIC_AUTH_ACTIVE: 'true',
        N8N_BASIC_AUTH_USER: 'nexus',
        N8N_BASIC_AUTH_PASSWORD: 'CK-Nexus-2026!',
        N8N_PROTOCOL: 'http',
        NODE_ENV: 'production'
      },
      autorestart: true,
      watch: false,
      max_restarts: 5
    },
    // AnyClaw Autonomous Agent
    {
      name: 'anyclaw',
      script: 'node',
      args: 'src/cli/anyclaw.js start',
      cwd: '/workspace/anyclaw',
      env: {
        PORT: 18789,
        NODE_ENV: 'production'
      },
      autorestart: true,
      watch: false
    },
    // OpenCode Server
    {
      name: 'opencode',
      script: 'opencode',
      args: 'serve',
      cwd: '/workspace/opencode',
      env: {
        PORT: 18924,
        OPENCODE_SERVER_PASSWORD: 'ck-nexus-2026-secure'
      },
      autorestart: true,
      watch: false
    },
    // Ollama Local AI
    {
      name: 'ollama',
      script: 'ollama',
      args: 'serve',
      env: {
        OLLAMA_HOST: '0.0.0.0:11434',
        OLLAMA_ORIGINS: '*'
      },
      autorestart: true,
      watch: false
    }
  ]
};
