// src/index.js （或你的项目入口 index.js）
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';

import { CopilotKit } from '@copilotkit/react-core';
import '@copilotkit/react-ui/styles.css';

const root = ReactDOM.createRoot(document.getElementById('root'));

root.render(
  <React.StrictMode>
    {/* 重新包上 CopilotKit，但 runtimeUrl 换成同源路径，避免 CORS */}
    <CopilotKit runtimeUrl="/copilotkit">
      <App />
    </CopilotKit>
  </React.StrictMode>
);
