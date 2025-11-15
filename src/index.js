// src/index.js （或你的项目入口 index.js）
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';

import { CopilotKit } from '@copilotkit/react-core';
import '@copilotkit/react-ui/styles.css';

const root = ReactDOM.createRoot(document.getElementById('root'));

root.render(
  <React.StrictMode>
    {/* CopilotKit runtimeUrl 指向 FastAPI 后端的 CopilotKit 端点 */}
    <CopilotKit runtimeUrl="http://localhost:8000/copilotkit_remote">
      <App />
    </CopilotKit>
  </React.StrictMode>
);
