import React from 'react';
import './App.css';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Landing from './pages/Landing';
import Terminal from './pages/Terminal';

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/terminal" element={<Terminal />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
