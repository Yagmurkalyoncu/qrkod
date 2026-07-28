import React from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import Header from './components/Header';
import BottomNav from './components/BottomNav';
import MainScreen from './pages/MainScreen';
import AutomationScreen from './pages/AutomationScreen';

function AppLayout() {
  const location = useLocation();

  return (
    <div style={{ paddingBottom: '100px' }}>
      <Header />
      <main className="dashboard-container">
        <Routes>
          <Route path="/" element={<MainScreen />} />
          <Route path="/otomasyon" element={<AutomationScreen />} />
        </Routes>
      </main>
      <BottomNav currentPath={location.pathname} />
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}

export default App;
