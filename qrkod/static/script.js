document.addEventListener('DOMContentLoaded', () => {

    // --- DOM ELEMENTS (ADMIN) ---
    const formAdd = document.getElementById('form-add-automation');
    const tableBody = document.getElementById('table-body');
    const searchInput = document.getElementById('search-input');
    
    // Popups
    const popupOverlay = document.getElementById('popup-overlay');
    const popupMsg = document.getElementById('popup-msg');
    const btnPopupOk = document.getElementById('btn-popup-ok');
    
    const deleteOverlay = document.getElementById('delete-overlay');
    const btnDeleteCancel = document.getElementById('btn-delete-cancel');
    const btnDeleteConfirm = document.getElementById('btn-delete-confirm');

    let automationsList = {};
    let activeAutoId = null;
    let deleteConfirmId = null;

    // --- POPUP UTILS ---
    function showAlert(msg) {
        popupMsg.textContent = msg;
        popupOverlay.classList.remove('hidden');
    }
    
    btnPopupOk.addEventListener('click', () => {
        popupOverlay.classList.add('hidden');
    });

    btnDeleteCancel.addEventListener('click', () => {
        deleteOverlay.classList.add('hidden');
        deleteConfirmId = null;
    });

    btnDeleteConfirm.addEventListener('click', () => {
        if (deleteConfirmId) {
            fetch(`/api/automations/${deleteConfirmId}`, { method: 'DELETE' })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        delete automationsList[deleteConfirmId];
                        if (activeAutoId === deleteConfirmId) activeAutoId = null;
                        renderTable();
                    }
                });
        }
        deleteOverlay.classList.add('hidden');
    });

    // --- FETCH & RENDER TABLE ---
    function fetchAutomations() {
        fetch('/api/automations')
            .then(res => res.json())
            .then(data => {
                automationsList = data;
                renderTable();
            });
    }

    function renderTable() {
        const query = searchInput.value.toLowerCase();
        tableBody.innerHTML = '';
        
        let hasRows = false;
        
        for (const [id, auto] of Object.entries(automationsList)) {
            if (!auto.name.toLowerCase().includes(query)) continue;
            hasRows = true;

            const tr = document.createElement('tr');
            
            // SEÇ (Radio)
            const isChecked = activeAutoId === id ? 'checked' : '';
            const tdSelect = `<td style="text-align: center;"><input type="radio" name="auto-select" class="radio-select" value="${id}" ${isChecked}></td>`;
            
            // NAME
            const tdName = `<td style="font-weight: 800; color: rgb(0, 45, 122);">${auto.name}</td>`;
            
            // TYPE
            const tdType = `<td>${auto.kabin_tipi}</td>`;
            
            // HEIGHT / X Y Z
            const tdPhys = `
                <td>
                    <div style="display:flex; align-items:center; gap:5px;">
                        Boy: <input type="number" step="0.01" class="table-input" value="${auto.fiziksel_parametreler.kabin_yuksekligi_m}" data-id="${id}" data-field="kabin_yuksekligi_m">m
                    </div>
                    <div style="display:flex; align-items:center; gap:5px; margin-top:5px;">
                        X: &nbsp;&nbsp;&nbsp;&nbsp;<input type="number" step="0.01" class="table-input" style="width: 60px;" value="${auto.fiziksel_parametreler.qr_koordinatlari.x}" data-id="${id}" data-field="x_koordinati">
                        Y: <input type="number" step="0.01" class="table-input" style="width: 60px;" value="${auto.fiziksel_parametreler.qr_koordinatlari.y}" data-id="${id}" data-field="y_koordinati">
                        Z: <input type="number" step="0.01" class="table-input" style="width: 60px;" value="${auto.fiziksel_parametreler.qr_koordinatlari.z}" data-id="${id}" data-field="z_koordinati">
                    </div>
                </td>`;
            
            // TOLERANCES
            const tdTols = `
                <td style="text-align: center;">
                    <div style="display:inline-flex; align-items:center; gap:5px;">
                        Mesafe: <input type="number" step="0.01" class="table-input" value="${auto.analiz_toleranslari.mesafe_toleransi}" data-id="${id}" data-field="mesafe_toleransi">
                    </div>
                    <br>
                    <div style="display:inline-flex; align-items:center; gap:5px; margin-top:5px;">
                        Açı: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<input type="number" step="0.01" class="table-input" value="${auto.analiz_toleranslari.aci_toleransi}" data-id="${id}" data-field="aci_toleransi">
                    </div>
                    <br>
                    <div style="display:inline-flex; align-items:center; gap:5px; margin-top:5px;">
                        Derinlik (Z): <input type="number" step="0.01" class="table-input" value="${auto.analiz_toleranslari.derinlik_toleransi || 0.08}" data-id="${id}" data-field="derinlik_toleransi" style="width: 55px;">
                    </div>
                </td>`;
            
            // DELETE
            const tdDelete = `
                <td style="text-align: center;">
                    <button class="btn-delete" data-id="${id}">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        </svg>
                    </button>
                </td>`;
            
            tr.innerHTML = tdSelect + tdName + tdType + tdPhys + tdTols + tdDelete;
            tableBody.appendChild(tr);
        }

        if (!hasRows) {
            tableBody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:30px; color:#94a3b8;">Aranan kriterlere uygun otomasyon bulunamadı.</td></tr>`;
        }

        attachTableEvents();
    }

    function attachTableEvents() {
        // Radio Buttons (Select Target)
        document.querySelectorAll('.radio-select').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const selectedId = e.target.value;
                activeAutoId = selectedId;
                
                fetch('/api/set_target', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id: selectedId})
                }).then(res => res.json()).then(data => {
                    if (data.success) {
                        // Switch to Camera Tab via URL redirection
                        window.location.href = '/';
                    }
                });
            });
        });

        // Inputs (Update value on change)
        document.querySelectorAll('.table-input').forEach(input => {
            input.addEventListener('change', (e) => {
                const id = e.target.getAttribute('data-id');
                const field = e.target.getAttribute('data-field');
                const val = parseFloat(e.target.value);
                
                const payload = {};
                payload[field] = val;

                fetch(`/api/automations/${id}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                }).then(res => res.json()).then(data => {
                    if(data.success) {
                        if (field === "kabin_yuksekligi_m") automationsList[id].fiziksel_parametreler.kabin_yuksekligi_m = val;
                        else if (field === "x_koordinati") automationsList[id].fiziksel_parametreler.qr_koordinatlari.x = val;
                        else if (field === "y_koordinati") automationsList[id].fiziksel_parametreler.qr_koordinatlari.y = val;
                        else if (field === "z_koordinati") automationsList[id].fiziksel_parametreler.qr_koordinatlari.z = val;
                        else if (field === "mesafe_toleransi") automationsList[id].analiz_toleranslari.mesafe_toleransi = val;
                        else if (field === "aci_toleransi") automationsList[id].analiz_toleranslari.aci_toleransi = val;
                        else if (field === "derinlik_toleransi") automationsList[id].analiz_toleranslari.derinlik_toleransi = val;
                    }
                });
            });
        });

        // Delete Buttons
        document.querySelectorAll('.btn-delete').forEach(btn => {
            btn.addEventListener('click', (e) => {
                deleteConfirmId = e.currentTarget.getAttribute('data-id');
                deleteOverlay.classList.remove('hidden');
            });
        });
    }

    if (searchInput) {
        searchInput.addEventListener('input', renderTable);
    }

    // --- ADD AUTOMATION ---
    if (formAdd) {
        formAdd.addEventListener('submit', (e) => {
            e.preventDefault();
            const name = document.getElementById('new-name').value.trim();
            if (!name) return;

            // Check exists
            const exists = Object.values(automationsList).some(a => a.name.toLowerCase() === name.toLowerCase());
            if (exists) {
                showAlert(`"${name}" isimli otomasyon sistemde zaten kayıtlı.`);
                return;
            }

            const payload = {
                name: name,
                kabin_tipi: document.getElementById('new-type').value,
                kabin_yuksekligi_m: document.getElementById('new-height').value,
                x_koordinati: document.getElementById('new-x').value,
                y_koordinati: document.getElementById('new-y').value,
                z_koordinati: document.getElementById('new-z').value,
                mesafe_toleransi: document.getElementById('new-dist-tol').value,
                aci_toleransi: document.getElementById('new-aspect-tol').value,
                derinlik_toleransi: document.getElementById('new-depth-tol').value
            };

            fetch('/api/automations', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(response => {
                if (response.success) {
                    automationsList[response.id] = response.data;
                    renderTable();
                    formAdd.reset();
                    document.getElementById('new-height').value = "2.50";
                    document.getElementById('new-z').value = "2.15";
                    document.getElementById('new-dist-tol').value = "0.05";
                    document.getElementById('new-aspect-tol').value = "0.20";
                    document.getElementById('new-depth-tol').value = "0.08";
                }
            });
        });
    }

    // --- LIVE CONTROLS (MAIN SCREEN) ---
    const liveDistTol = document.getElementById('live-dist-tol');
    const liveAspectTol = document.getElementById('live-aspect-tol');
    const liveDepthTol = document.getElementById('live-depth-tol');
    const btnToggleAnalysis = document.getElementById('btn-toggle-analysis');
    let isAnalyzing = true;

    function updateLiveControlsFromConfig(config) {
        if(liveDistTol) liveDistTol.value = config.DISTANCE_TOLERANCE;
        if(liveAspectTol) liveAspectTol.value = config.ASPECT_RATIO_TOLERANCE;
        if(liveDepthTol) liveDepthTol.value = config.DEPTH_TOLERANCE || 0.08;
        isAnalyzing = config.IS_ACTIVE;
        updateToggleBtnState();
    }

    function updateToggleBtnState() {
        if (!btnToggleAnalysis) return;
        
        const standbyOverlay = document.getElementById('standby-overlay');
        const videoStream = document.getElementById('video-stream');
        
        if (isAnalyzing) {
            btnToggleAnalysis.textContent = "DENETİMİ BİTİR";
            btnToggleAnalysis.classList.remove('btn-pause');
            if (standbyOverlay) standbyOverlay.classList.add('hidden');
            if (videoStream) videoStream.style.opacity = '1';
        } else {
            btnToggleAnalysis.textContent = "DENETİMİ BAŞLAT";
            btnToggleAnalysis.classList.add('btn-pause');
            if (standbyOverlay) standbyOverlay.classList.remove('hidden');
            if (videoStream) videoStream.style.opacity = '0.3'; // Kamarayı karart
        }
    }

    if (btnToggleAnalysis) {
        btnToggleAnalysis.addEventListener('click', () => {
            isAnalyzing = !isAnalyzing;
            updateToggleBtnState();
            fetch('/api/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({IS_ACTIVE: isAnalyzing})
            });
        });
    }

    if (liveDistTol && liveAspectTol) {
        [liveDistTol, liveAspectTol, liveDepthTol].forEach(input => {
            if (input) {
                input.addEventListener('change', () => {
                    fetch('/api/config', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            DISTANCE_TOLERANCE: parseFloat(liveDistTol.value),
                            ASPECT_RATIO_TOLERANCE: parseFloat(liveAspectTol.value),
                            DEPTH_TOLERANCE: parseFloat(liveDepthTol ? liveDepthTol.value : 0.08)
                        })
                    });
                    
                    if (activeAutoId && automationsList[activeAutoId]) {
                        automationsList[activeAutoId].analiz_toleranslari.mesafe_toleransi = parseFloat(liveDistTol.value);
                        automationsList[activeAutoId].analiz_toleranslari.aci_toleransi = parseFloat(liveAspectTol.value);
                        automationsList[activeAutoId].analiz_toleranslari.derinlik_toleransi = parseFloat(liveDepthTol ? liveDepthTol.value : 0.08);
                        
                        fetch(`/api/automations/${activeAutoId}`, {
                            method: 'PUT',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                mesafe_toleransi: parseFloat(liveDistTol.value),
                                aci_toleransi: parseFloat(liveAspectTol.value),
                                derinlik_toleransi: parseFloat(liveDepthTol ? liveDepthTol.value : 0.08)
                            })
                        });
                    }
                });
            }
        });
    }

    // --- CAMERA TAB METRICS (Poll state) ---
    const liveStatusEl = document.getElementById('live-status');
    const autoIdEl = document.getElementById('auto-id');
    const cabinetTypeEl = document.getElementById('cabinet-type');
    const qrCountEl = document.getElementById('qr-count');

    if (liveStatusEl) {
        setInterval(() => {
            fetch('/api/state')
                .then(response => response.json())
                .then(data => {
                    liveStatusEl.textContent = data.status;
                    autoIdEl.textContent = data.automation_id;
                    cabinetTypeEl.textContent = data.cabinet_type;
                    qrCountEl.textContent = data.qr_count;

                    liveStatusEl.className = 'status-text';
                    if (data.status.startsWith("KAPALI")) {
                        liveStatusEl.classList.add('safe');
                    } else if (data.status.startsWith("ACIK (Eksik")) {
                        liveStatusEl.classList.add('warning');
                    } else if (data.status.startsWith("ACIK")) {
                        liveStatusEl.classList.add('danger');
                    } else {
                        liveStatusEl.classList.add('unknown');
                    }
                })
                .catch(err => {});
        }, 500);
    }

    // Initial Load
    if (tableBody) {
        fetchAutomations();
    }
    
    fetch('/api/config').then(res => res.json()).then(config => {
        updateLiveControlsFromConfig(config);
    });
});
