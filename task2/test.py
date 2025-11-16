import requests
doc_url = "https://www.cityofventura.ca.gov/AgendaCenter/ViewFile/Agenda/_11042025-3522"
r = requests.get(doc_url)
if r.status_code == 200:
    print("Downloadable file found!")
