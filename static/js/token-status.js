// Token status handler
document.addEventListener('DOMContentLoaded', function() {
    // Aggiungi div token-status se non esiste
    const header = document.querySelector('.header');
    if (!document.getElementById('token-status')) {
        const tokenStatusDiv = document.createElement('div');
        tokenStatusDiv.id = 'token-status';
        tokenStatusDiv.className = 'token-status';
        tokenStatusDiv.textContent = 'Verifica token in corso...';
        header.appendChild(tokenStatusDiv);
    }

    // Funzione per verificare lo stato del token
    function checkTokenStatus() {
        const tokenStatusElement = document.getElementById('token-status');
        
        fetch('/api/token-status')
            .then(response => response.json())
            .then(data => {
                // Rimuovi tutte le classi di stato esistenti
                tokenStatusElement.classList.remove('token-valid', 'token-invalid', 'token-error');
                
                if (data.valid) {
                    // Token valido
                    tokenStatusElement.textContent = '✅ ' + data.message;
                    tokenStatusElement.classList.add('token-valid');
                } else if (data.mode === 'simulazione') {
                    // Token non valido - modalità simulazione
                    tokenStatusElement.textContent = '⚠️ ' + data.message;
                    tokenStatusElement.classList.add('token-invalid');
                } else {
                    // Errore
                    tokenStatusElement.textContent = '❌ ' + data.message;
                    tokenStatusElement.classList.add('token-error');
                }
            })
            .catch(error => {
                console.error('Errore verifica token:', error);
                tokenStatusElement.textContent = '❌ Errore verifica token';
                tokenStatusElement.classList.add('token-error');
            });
    }
    
    // Verifica lo stato del token all'avvio
    checkTokenStatus();
    
    // Aggiorna lo stato ogni 5 minuti
    setInterval(checkTokenStatus, 300000);
});
