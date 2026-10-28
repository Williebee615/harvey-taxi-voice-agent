"""Exact quotes from real case files; unknown documents never receive invented text."""
from agent_kit.evidence import documents


def get_page_text(root, document_id, page=1, case_name='harvey-taxi-ada-doctor-visit'):
    if page != 1:
        return ''
    return documents(root, case_name).get(document_id, '')


def verify_quote(root, document_id, page, quote, case_name='harvey-taxi-ada-doctor-visit'):
    text = get_page_text(root, document_id, page, case_name)
    return bool(isinstance(quote, str) and quote.strip() and quote in text)
