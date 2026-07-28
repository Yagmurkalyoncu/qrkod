import React, { useEffect, useState } from 'react';
import { Settings, ShieldCheck, Zap, Server } from 'lucide-react';

const API_URL = 'http://localhost:5000/api';
const VIDEO_URL = 'http://localhost:5000/video_feed';

function MainScreen() {
  const [state, setState] = useState({
    status: 'BEKLENİYOR',
    cabinet_type: 'Bilinmiyor',
    automation_id: 'Seçilmedi',
    qr_count: 0
  });

  const [config, setConfig] = useState({
    IS_ACTIVE: true
  });

  useEffect(() => {
    const fetchState = async () => {
      try {
        const res = await fetch(`${API_URL}/state`);
        const data = await res.json();
        setState(data);
      } catch (err) {
        console.error("API Bağlantı Hatası:", err);
      }
    };
    const interval = setInterval(fetchState, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await fetch(`${API_URL}/config`);
        const data = await res.json();
        setConfig(data);
      } catch (err) {
        console.error("Config Hatası:", err);
      }
    };
    fetchConfig();
  }, []);

  const toggleSystem = async () => {
    const newActive = !config.IS_ACTIVE;
    try {
      const res = await fetch(`${API_URL}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ IS_ACTIVE: newActive })
      });
      const data = await res.json();
      setConfig(prev => ({ ...prev, IS_ACTIVE: data.IS_ACTIVE }));
    } catch (err) {
      console.error(err);
    }
  };

  const isClosed = state.status.includes('KAPALI');
  const isStopped = !config.IS_ACTIVE || state.status === 'DURDURULDU';
  let badgeClass = 'badge-wait';
  if (isStopped) badgeClass = 'badge-wait';
  else if (isClosed) badgeClass = 'badge-success';
  else if (state.status.includes('ACIK')) badgeClass = 'badge-danger';

  return (
    <div className="tab-content active" id="camera-tab">
      
      <div className="metrics-row">
        <div className="metric-card">
          <span className="metric-title">GÜNCEL DURUM</span>
          <h1 className={`status-text ${isStopped ? 'unknown' : (isClosed ? 'success' : 'danger')}`}>
            {isStopped ? 'DURDURULDU' : state.status}
          </h1>
          <span className="metric-desc">Anlık Sensör Analizi</span>
        </div>
        <div className="metric-card">
          <span className="metric-title">AKTİF OTOMASYON HEDEFİ</span>
          <h2 style={{color:'var(--primary-color)'}}>{state.automation_id}</h2>
          <span className="metric-desc">Robotun Navigasyon Hedefi</span>
        </div>
        <div className="metric-card">
          <span className="metric-title">KABİN TİPİ</span>
          <h2>{state.cabinet_type}</h2>
          <span className="metric-desc">Fiziksel Kabin Türü</span>
        </div>
        <div className="metric-card">
          <span className="metric-title">GÖRÜNEN QR SAYISI</span>
          <h2>{state.qr_count} / 2 Adet</h2>
          <span className="metric-desc">Kameradaki Referanslar</span>
        </div>
      </div>

      <div className="main-screen-layout">
        <div className="card camera-card">
          <div className="card-header">
            <h3>Canlı Otonom Kamera Yayını</h3>
            <div className={`live-indicator ${!config.IS_ACTIVE ? 'hidden' : ''}`}></div>
          </div>
          <div className="camera-wrapper">
            <img src={VIDEO_URL} alt="Kamera Yayını" id="video-stream" className={!config.IS_ACTIVE ? 'dimmed' : ''} style={{width:'100%', borderRadius:'8px', display:'block'}}/>
            
            {!config.IS_ACTIVE && (
              <div className="standby-overlay" id="standby-overlay">
                <Zap size={64} style={{marginBottom:'16px', opacity:0.8}} />
                <h2>SİSTEM BEKLEMEDE</h2>
                <p>Kamera şu anda duraklatıldı.</p>
              </div>
            )}
          </div>
        </div>

        <div className="live-controls">
          <h3>Canlı Denetim Ayarları</h3>
          <p>Kameraya yansıyan tolerans limitlerini anlık olarak buradan değiştirebilirsiniz.</p>
          
          <div className="input-group">
            <label>MESAFE TOLERANSI (Sürgülü)</label>
            <input type="number" step="0.01" value={config.DISTANCE_TOLERANCE || 0.05} readOnly />
          </div>

          <div className="input-group">
            <label>AÇI TOLERANSI (Menteşeli)</label>
            <input type="number" step="0.01" value={config.ASPECT_RATIO_TOLERANCE || 0.20} readOnly />
          </div>

          <div className="control-actions">
            <button 
              onClick={toggleSystem}
              className={`btn-primary ${!config.IS_ACTIVE ? '' : 'active'}`}
            >
              {config.IS_ACTIVE ? 'DENETİMİ BİTİR' : 'DENETİMİ BAŞLAT'}
            </button>
          </div>
        </div>
      </div>

    </div>
  );
}

export default MainScreen;
