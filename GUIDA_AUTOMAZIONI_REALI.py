#!/usr/bin/env python3
"""
Guida per implementare automazioni reali nel sistema di cambio stato progetti
"""

# ESEMPIO 1: Integrazione con eliminazione ore esistente
def auto_delete_draft_hours_real(project_id):
    """Elimina le ore bozza/temporanee per un progetto - VERSIONE REALE"""
    try:
        # Integra con la tua funzione esistente
        from delete_qb_time_activities import delete_time_activities_for_project
        
        # Elimina solo le ore con status "Draft" o simile
        result = delete_time_activities_for_project(
            project_id=project_id,
            status_filter="Draft"  # Personalizza secondo la tua logica
        )
        
        return f"Eliminate {result.get('deleted_count', 0)} ore bozza"
    except Exception as e:
        return f"Errore eliminazione ore bozza: {str(e)}"

# ESEMPIO 2: Integrazione con creazione fatture
def auto_generate_final_invoice_real(project_id):
    """Genera fattura finale per progetto completato - VERSIONE REALE"""
    try:
        from create_or_update_invoice_for_project import create_or_update_invoice_for_project
        
        # Crea la fattura finale
        result = create_or_update_invoice_for_project(
            project_id=project_id,
            final=True  # Marca come fattura finale
        )
        
        if result.get('success'):
            return f"Fattura finale generata: {result.get('invoice_id')}"
        else:
            return f"Errore generazione fattura: {result.get('error')}"
    except Exception as e:
        return f"Errore generazione fattura: {str(e)}"

# ESEMPIO 3: Integrazione con QuickBooks customers
def auto_create_subcustomer_real(project_id):
    """Crea sub-customer in QuickBooks per progetto confermato - VERSIONE REALE"""
    try:
        from qb_customer import create_or_update_customer_for_project
        
        # Recupera i dati del progetto da Rentman
        from rentman_api import get_project_and_customer
        project_data = get_project_and_customer(project_id)
        
        # Crea il sub-customer
        result = create_or_update_customer_for_project(
            project_id=project_id,
            project_data=project_data['project'],
            customer_data=project_data['customer']
        )
        
        if result.get('success'):
            return f"Sub-customer creato: {result.get('customer_name')}"
        else:
            return f"Errore creazione sub-customer: {result.get('error')}"
    except Exception as e:
        return f"Errore creazione sub-customer: {str(e)}"

# ESEMPIO 4: Notifiche email
def auto_notify_project_completion_real(project_id):
    """Invia notifica email di completamento progetto - VERSIONE REALE"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Configura i dettagli email (personalizza)
        smtp_server = "your-smtp-server.com"
        smtp_port = 587
        email_user = "your-email@company.com"
        email_pass = "your-password"
        
        # Destinatari (personalizza)
        to_emails = ["manager@company.com", "accounting@company.com"]
        
        # Crea messaggio
        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = ", ".join(to_emails)
        msg['Subject'] = f"Progetto {project_id} Completato"
        
        body = f"""
        Il progetto {project_id} è stato marcato come RIENTRATO.
        
        Azioni automatiche eseguite:
        - Ore bozza eliminate
        - Fattura finale generata
        
        Verifica i dettagli nel sistema.
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Invia email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_user, email_pass)
        server.send_message(msg)
        server.quit()
        
        return f"Notifica inviata a {len(to_emails)} destinatari"
    except Exception as e:
        return f"Errore invio notifica: {str(e)}"

# ISTRUZIONI PER IMPLEMENTARE:
"""
1. Copia le funzioni che ti interessano
2. Sostituisci le funzioni placeholder in db_config.py
3. Personalizza i parametri per il tuo ambiente
4. Testa con progetti reali

ESEMPIO DI SOSTITUZIONE in db_config.py:

# Sostituisci questa funzione placeholder:
def auto_delete_draft_hours(project_id):
    return "Simulato - Ore bozza eliminate"

# Con questa versione reale:  
def auto_delete_draft_hours(project_id):
    return auto_delete_draft_hours_real(project_id)  # Chiama la funzione reale
"""
