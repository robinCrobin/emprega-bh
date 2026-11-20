import React from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

function App() {
  return <main>
    <h1>EmpregaBH</h1>
    <p>Ambiente inicial de desenvolvimento.</p>
    <p>A interface de consulta será integrada pela frente de frontend.</p>
  </main>;
}

createRoot(document.getElementById('root')).render(<App />);
