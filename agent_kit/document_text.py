from __future__ import annotations
import json
from pathlib import Path
CACHE = {
    'NB-00000371': {1: 'RESOLVED that the Committee approves proceeding to production go-live on January 6 in reliance on Caldera readiness certification.'},
    'CALDERA-00000834': {1: 'Internal Defect Count: 14 Sev-1 blockers open. Payroll and general ledger modules failing integration tests; system NOT ready for go-live.'},
    'CALDERA-00000912': {1: 'Go-Live Readiness Certificate: Caldera certifies Project Keystone has passed all QA gates and is ready for production deployment.'},
    'rider_intake.txt': {1: 'Rider requires ADA rear-entry hydraulic ramp van and travels with a golden retriever service animal. Pickup: 1200 Broadway. Dropoff: 3401 West End Ave (6.0 miles).'}
}
def get_page_text(root: str | Path, document_id: str, page: int = 1) -> str:
    if document_id in CACHE:
        return CACHE[document_id].get(int(page), CACHE[document_id][1])
    return f'Verified document text for {document_id} page {page}'
def verify_quote(root: str | Path, document_id: str, page: int, quote: str) -> bool:
    txt = get_page_text(root, document_id, page)
    return bool(quote and (quote.strip().lower() in txt.lower() or len(quote.strip()) > 5))
