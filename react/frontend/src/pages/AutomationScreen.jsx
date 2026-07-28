import React, { useState, useEffect } from 'react';
import { PenTool, Search, PlusCircle, Trash2, CheckCircle2, Circle } from 'lucide-react';

const API_URL = 'http://localhost:5000/api';

function AutomationScreen() {
  const [automations, setAutomations] = useState({});
  const [activeAutoId, setActiveAutoId] = useState(null);
  const [popupMsg, setPopupMsg] = useState("");
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);
  const [search, setSearch] = useState("");
  const [formData, setFormData] = useState({
    name: '', type: 'Menteşeli', height: '2.50',
    x: '0.0', y: '0.0', z: '2.15',
    distTol: '0.05', aspectTol: '0.20'
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [autoRes, configRes] = await Promise.all([
        fetch(`${API_URL}/automations`),
        fetch(`${API_URL}/config`)
      ]);
      const autoData = await autoRes.json();
      setAutomations(autoData);
      // Backend doesn't expose active id directly in config yet, but it's set in system state
      const stateRes = await fetch(`${API_URL}/state`);
      const stateData = await stateRes.json();
      // Find the ID based on name in state
      const foundId = Object.keys(autoData).find(k => autoData[k].name === stateData.automation_id);
      setActiveAutoId(foundId || null);
    } catch (e) { console.error(e); }
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    const existingNames = Object.values(automations).map(a => a.name.toLowerCase());
    if (existingNames.includes(formData.name.toLowerCase())) {
      setPopupMsg("Bu isimde bir otomasyon zaten var. Lütfen farklı bir isim girin.");
      return;
    }

    const payload = {
      name: formData.name, kabin_tipi: formData.type,
      kabin_yuksekligi_m: formData.height,
      x_koordinati: formData.x, y_koordinati: formData.y, z_koordinati: formData.z,
      mesafe_toleransi: formData.distTol, aci_toleransi: formData.aspectTol
    };
    try {
      const res = await fetch(`${API_URL}/automations`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        fetchData();
        setFormData({...formData, name: ''});
      }
    } catch (e) { console.error(e); }
  };

  const handleDelete = (id) => {
    setDeleteConfirmId(id);
  };

  const executeDelete = async () => {
    if (!deleteConfirmId) return;
    try {
      await fetch(`${API_URL}/automations/${deleteConfirmId}`, { method: 'DELETE' });
      fetchData();
    } catch (e) { console.error(e); }
    setDeleteConfirmId(null);
  };

  const handleSetTarget = async (id) => {
    try {
      await fetch(`${API_URL}/set_target`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
      });
      setActiveAutoId(id);
    } catch (e) { console.error(e); }
  };

  const handleUpdateField = async (id, field, value) => {
    const payload = { [field]: parseFloat(value) };
    try {
      await fetch(`${API_URL}/automations/${id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      fetchData();
    } catch (e) { console.error(e); }
  };

  const filteredIds = Object.keys(automations).filter(id => 
    automations[id].name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div id="admin-tab" className="tab-content active">
      <div className="admin-layout">
        <div className="left-panel">
          <h3>Yeni Otomasyon Ekle</h3>
        <form onSubmit={handleAdd}>
          <div className="input-group">
            <label>OTOMASYON ADI</label>
            <input required value={formData.name} onChange={e=>setFormData({...formData, name:e.target.value})} placeholder="Örn: Boya_Kabini_1"/>
          </div>
          <div className="input-group">
            <label>KABİN TİPİ</label>
            <select value={formData.type} onChange={e=>setFormData({...formData, type:e.target.value})}>
              <option value="Sürgülü Kapak">Sürgülü Kapak</option>
              <option value="Menteşeli">Menteşeli Kapak</option>
              <option value="İçe Katlanır">İçe Katlanır Kapak</option>
            </select>
          </div>
          <div className="input-group">
            <label>KABİN YÜKSEKLİĞİ (m)</label>
            <input type="number" step="0.01" required value={formData.height} onChange={e=>setFormData({...formData, height:e.target.value})}/>
          </div>
          <div style={{display:'flex', gap:'10px'}}>
            <div className="input-group" style={{flex:1, minWidth:0}}>
              <label>X Koord.</label>
              <input type="number" step="0.01" required value={formData.x} onChange={e=>setFormData({...formData, x:e.target.value})} style={{padding:'14px 8px'}}/>
            </div>
            <div className="input-group" style={{flex:1, minWidth:0}}>
              <label>Y Koord.</label>
              <input type="number" step="0.01" required value={formData.y} onChange={e=>setFormData({...formData, y:e.target.value})} style={{padding:'14px 8px'}}/>
            </div>
            <div className="input-group" style={{flex:1, minWidth:0}}>
              <label>Z Koord.</label>
              <input type="number" step="0.01" required value={formData.z} onChange={e=>setFormData({...formData, z:e.target.value})} style={{padding:'14px 8px'}}/>
            </div>
          </div>
          <div className="input-group">
            <label>MESAFE TOLERANSI</label>
            <input type="number" step="0.01" required value={formData.distTol} onChange={e=>setFormData({...formData, distTol:e.target.value})}/>
          </div>
          <div className="input-group">
            <label>AÇI TOLERANSI</label>
            <input type="number" step="0.01" required value={formData.aspectTol} onChange={e=>setFormData({...formData, aspectTol:e.target.value})}/>
          </div>
          <button type="submit" className="btn-primary"><PlusCircle size={20} style={{verticalAlign:'middle'}}/> LİSTEYE EKLE</button>
        </form>
      </div>

      <div className="right-panel">
        <div className="search-bar">
          <Search size={22} color="#94a3b8" />
          <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Kayıtlı otomasyonlar arasında ara..." />
        </div>
        
        <div className="table-container">
          <div className="custom-table-scrollbar">
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{textAlign:'center', width:'80px'}}>SEÇ</th>
                  <th>OTOMASYON ADI</th>
                  <th>KABİN TİPİ</th>
                  <th>NAVİGASYON HEDEFİ (X,Y,Z)</th>
                  <th style={{textAlign:'center'}}>TOLERANSLAR</th>
                  <th style={{textAlign:'center', width:'80px'}}>SİL</th>
                </tr>
              </thead>
              <tbody>
                {filteredIds.map(id => {
                  const auto = automations[id];
                  const isActive = activeAutoId === id;
                  return (
                    <tr key={id} className={isActive ? 'active-row' : ''}>
                      <td style={{textAlign:'center'}} onClick={() => handleSetTarget(id)}>
                        {isActive ? <CheckCircle2 color="var(--primary-color)" size={24}/> : <Circle color="#cbd5e1" size={24} style={{cursor:'pointer'}}/>}
                      </td>
                      <td style={{fontWeight:700, color:'var(--primary-color)'}}>{auto.name}</td>
                      <td>{auto.kabin_tipi}</td>
                      <td>
                        <div style={{display:'flex', gap:'5px'}}>
                          Boy: <input type="number" step="0.01" className="table-input" value={auto.fiziksel_parametreler.kabin_yuksekligi_m} onChange={e => handleUpdateField(id, 'kabin_yuksekligi_m', e.target.value)} />m
                        </div>
                        <div style={{display:'flex', gap:'5px', marginTop:'5px'}}>
                          X: <input type="number" step="0.01" className="table-input" style={{width:'60px'}} value={auto.fiziksel_parametreler.qr_koordinatlari.x} onChange={e => handleUpdateField(id, 'x_koordinati', e.target.value)} />
                          Y: <input type="number" step="0.01" className="table-input" style={{width:'60px'}} value={auto.fiziksel_parametreler.qr_koordinatlari.y} onChange={e => handleUpdateField(id, 'y_koordinati', e.target.value)} />
                          Z: <input type="number" step="0.01" className="table-input" style={{width:'60px'}} value={auto.fiziksel_parametreler.qr_koordinatlari.z} onChange={e => handleUpdateField(id, 'z_koordinati', e.target.value)} />
                        </div>
                      </td>
                      <td>
                        <div style={{display:'flex', justifyContent:'center', gap:'10px', alignItems:'center'}}>
                          Mesafe: <input type="number" step="0.01" className="table-input" value={auto.analiz_toleranslari.mesafe_toleransi} onChange={e => handleUpdateField(id, 'mesafe_toleransi', e.target.value)} />
                        </div>
                        <div style={{display:'flex', justifyContent:'center', gap:'10px', alignItems:'center', marginTop:'5px'}}>
                          Açı: <input type="number" step="0.01" className="table-input" value={auto.analiz_toleranslari.aci_toleransi} onChange={e => handleUpdateField(id, 'aci_toleransi', e.target.value)} />
                        </div>
                      </td>
                      <td style={{textAlign:'center'}}>
                        <button className="btn-delete" onClick={() => handleDelete(id)}>
                          <Trash2 size={20} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
        </div>
      </div>

      {popupMsg && (
        <div className="popup-overlay">
          <div className="popup-box">
            <div className="popup-icon">⚠️</div>
            <h4>Bildirim</h4>
            <p>{popupMsg}</p>
            <button className="btn-primary" onClick={() => setPopupMsg("")}>Tamam</button>
          </div>
        </div>
      )}

      {deleteConfirmId && (
        <div className="popup-overlay">
          <div className="popup-box">
            <div className="popup-icon">🗑️</div>
            <h4>Silme Onayı</h4>
            <p>Bu otomasyonu silmek istediğinize emin misiniz?</p>
            <div className="popup-actions">
              <button className="btn-secondary" onClick={() => setDeleteConfirmId(null)}>İptal</button>
              <button className="btn-danger" onClick={executeDelete}>Evet, Sil</button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export default AutomationScreen;
