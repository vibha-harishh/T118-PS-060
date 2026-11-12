import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn, ChildProcess } from 'child_process';
import { createServer as createViteServer } from 'vite';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = 3000;
const PYTHON_PORT = 5050;
let pythonProcess: ChildProcess | null = null;

function startPythonBackend() {
  console.log('[Node] Spawning Python Backend on port', PYTHON_PORT);
  pythonProcess = spawn('python3', ['backend/server.py'], {
    cwd: __dirname,
    stdio: 'inherit',
    env: { ...process.env, PYTHON_PORT: String(PYTHON_PORT) }
  });

  pythonProcess.on('exit', (code, signal) => {
    console.log(`[Python] Server exited with code ${code} and signal ${signal}`);
  });
}

async function startServer() {
  startPythonBackend();

  // Wait briefly for Python server to bind
  await new Promise((r) => setTimeout(r, 600));

  const app = express();
  app.use(express.json({ limit: '50mb' }));
  app.use(express.urlencoded({ limit: '50mb', extended: true }));

  // Proxy /api/* to Python backend
  app.all('/api/*', async (req, res) => {
    const targetUrl = `http://127.0.0.1:${PYTHON_PORT}${req.originalUrl}`;
    try {
      const headers: Record<string, string> = {};
      if (req.headers['content-type']) {
        headers['content-type'] = req.headers['content-type'] as string;
      }
      if (req.headers['authorization']) {
        headers['authorization'] = req.headers['authorization'] as string;
      }

      const options: RequestInit = {
        method: req.method,
        headers,
      };

      if (['POST', 'PUT', 'PATCH'].includes(req.method) && req.body) {
        options.body = JSON.stringify(req.body);
        headers['content-type'] = 'application/json';
      }

      const pyRes = await fetch(targetUrl, options);
      res.status(pyRes.status);

      // Forward headers
      pyRes.headers.forEach((val, key) => {
        if (!['content-encoding', 'content-length'].includes(key.toLowerCase())) {
          res.setHeader(key, val);
        }
      });

      const contentType = pyRes.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        const json = await pyRes.json();
        res.json(json);
      } else {
        const text = await pyRes.text();
        res.send(text);
      }
    } catch (err: any) {
      console.error('[Proxy Error]', err.message);
      res.status(502).json({ error: 'Failed to communicate with Python backend', detail: err.message });
    }
  });

  const isDev = process.env.NODE_ENV !== 'production';

  if (isDev) {
    const vite = await createViteServer({
      configFile: path.resolve(__dirname, 'vite.config.ts'),
      server: {
        middlewareMode: true,
        hmr: false,
        watch: null,
      },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static(path.resolve(__dirname, 'dist')));
    app.get('*', (_req, res) => {
      res.sendFile(path.resolve(__dirname, 'dist', 'index.html'));
    });
  }

  const server = app.listen(PORT, '0.0.0.0', () => {
    console.log(`[FullStack] Express + Vite running at http://0.0.0.0:${PORT}`);
  });

  const cleanExit = () => {
    if (pythonProcess) {
      pythonProcess.kill();
    }
    server.close(() => process.exit(0));
  };

  process.on('SIGINT', cleanExit);
  process.on('SIGTERM', cleanExit);
}

startServer().catch((err) => {
  console.error('[Server Start Error]', err);
  process.exit(1);
});
