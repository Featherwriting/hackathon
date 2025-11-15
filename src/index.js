import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';

import { CopilotKit } from '@copilotkit/react-core'
import '@copilotkit/react-ui/styles.css'


const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    {/* <CopilotKit runtimeUrl={import.meta.env.VITE_COPILOTKIT_RUNTIME_URL || '/copilotkit'}> */}
    <CopilotKit runtimeUrl="https://cloud.copilotkit.ai/api/runtime">
      <App />
    </CopilotKit>
  </React.StrictMode>
);

