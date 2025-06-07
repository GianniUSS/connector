def map_rentman_to_qbo_customer(customer):
    """
    Mappa i dati di un cliente Rentman in customer QBO.
    - Usa 'displayname' se presente, altrimenti 'name'.
    - NON fa escape degli apostrofi qui: l'escape va fatto solo nella query SQL verso QuickBooks.
    - Il payload JSON deve contenere il nome originale, con apostrofi singoli se presenti.
    """
    displayname = customer.get("displayname")
    if not displayname:
        displayname = customer.get("name", "Cliente senza nome")
    # NESSUN escape qui: l'escape va fatto solo nella query SQL, non nel payload JSON
    return {
        "DisplayName": displayname,
        "CompanyName": customer.get("company", customer.get("name", "")),
        "PrimaryEmailAddr": {"Address": customer.get("email", "no@email.it")},
        "PrimaryPhone": {"FreeFormNumber": customer.get("phone", "")},
        "BillAddr": {
            "Line1": customer.get("address", ""),
            "City": customer.get("city", ""),
            "CountrySubDivisionCode": customer.get("province", ""),
            "PostalCode": customer.get("postalcode", ""),
            "Country": customer.get("country", "Italy")
        },
        "Taxable": True,
        "TaxRegistrationNumber": customer.get("vat_number", "")
    }



def map_rentman_to_qbo_subcustomer(project):
    """Mappa i dati di progetto Rentman in sub-customer QBO seguendo il tuo esempio reale."""
    data = {
        "DisplayName": project.get("name", "Progetto senza nome"),
        "BillWithParent": True,
    }

    # CustomField se già configurati in QBO
    custom_fields = []
    if project.get("number"):
        custom_fields.append({
            "Name": "Numero Progetto",
            "Type": "StringType",
            "StringValue": str(project.get("number"))
        })
    if project.get("start_date"):
        custom_fields.append({
            "Name": "Data Inizio",
            "Type": "StringType",
            "StringValue": project.get("start_date")
        })
    if project.get("end_date"):
        custom_fields.append({
            "Name": "Data Fine",
            "Type": "StringType",
            "StringValue": project.get("end_date")
        })
    if project.get("status"):
        custom_fields.append({
            "Name": "Stato Progetto",
            "Type": "StringType",
            "StringValue": project.get("status")
        })
    if custom_fields:
        data["CustomField"] = custom_fields

    # ShipAddr: indirizzo lavoro/cantiere, se vuoi mostrarlo sul sub-customer
    if project.get("address"):
        data["ShipAddr"] = {
            "Line1": project.get("address"),
            "City": project.get("city", ""),
            "CountrySubDivisionCode": project.get("province", ""),
            "PostalCode": project.get("postalcode", ""),
            "Country": project.get("country", "Italy")
        }

    # Puoi aggiungere qui altri dati "fissi" che vuoi avere su tutti i progetti/sub-customer

    return data
