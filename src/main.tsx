import {createRoot} from 'react-dom/client';
import App from './App.tsx';
import './index.css';

if (typeof window !== 'undefined') {
  window.addEventListener('unhandledrejection', (e) => {
    if (e.reason?.message?.includes('WebSocket') || e.reason?.stack?.includes('@vite/client')) {
      e.preventDefault();
    }
  });
}

createRoot(document.getElementById('root')!).render(<App />);
