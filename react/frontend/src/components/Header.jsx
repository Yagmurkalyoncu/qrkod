import { Bell, ClipboardList, BookOpen, ExternalLink } from 'lucide-react';

function Header() {
  return (
    <header className="header2">
      <div className="header-content2">
        <div className="logo2">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
            <polyline points="2 17 12 22 22 17"></polyline>
            <polyline points="2 12 12 17 22 12"></polyline>
          </svg>
        </div>
        <div className="title-container2">
          <div className="title-text">ROBOTİK OTOMASYON MÜDÜRLÜĞÜ</div>
          <div className="subtitle-text">Otomasyon Komuta Merkezi</div>
        </div>
        <div className="icons">
          <a className="icon-container" href="#" title="Sistem Bildirimleri">
            <Bell size={24} />
          </a>
          <a className="icon-container" href="#" title="Kalite Kontrol Listesi">
            <ClipboardList size={24} />
          </a>
          <a className="icon-container" href="#" title="Dahili İletişim Rehberi">
            <BookOpen size={24} />
          </a>
          <a className="icon-container" href="#" title="ROM Ana Veri Sayfası">
            <ExternalLink size={24} />
          </a>
        </div>
      </div>
    </header>
  );
}

export default Header;
