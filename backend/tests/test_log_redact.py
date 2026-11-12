"""🔒 Audit 2026-11-12 #6: the logs held the Helius ?api-key= and ?session=<token>. Access lines are masked; httpx speaks only on warnings."""
import logging

import http_ctx


def test_access_lines_mask_secret_query_values():
    rec = logging.LogRecord('uvicorn.access', logging.INFO, __file__, 1, '%s - "%s %s HTTP/%s" %d',
                            ('127.0.0.1:5', 'GET', '/api/x?session=abc123&chain=solana&api-key=K9', '1.1', 200), None)
    assert http_ctx._Redact().filter(rec)
    line = rec.getMessage()
    assert 'abc123' not in line and 'K9' not in line and 'chain=solana' in line and 'session=[redacted]' in line


def test_httpx_no_longer_logs_every_url():
    assert logging.getLogger('httpx').getEffectiveLevel() >= logging.WARNING
