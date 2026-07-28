import React from 'react';
import { Link } from 'react-router-dom';
import { LayoutDashboard, PenTool } from 'lucide-react';

function BottomNav({ currentPath }) {
  return (
    <nav className="bottom-nav-bar">
      <Link to="/" className={`nav-item ${currentPath === '/' ? 'active' : ''}`} style={{textDecoration: 'none'}}>
        <LayoutDashboard size={24} />
        <span>Ana Ekran (Tespit)</span>
      </Link>
      <Link to="/otomasyon" className={`nav-item ${currentPath === '/otomasyon' ? 'active' : ''}`} style={{textDecoration: 'none'}}>
        <PenTool size={24} />
        <span>Otomasyon Ekranı</span>
      </Link>
    </nav>
  );
}

export default BottomNav;
