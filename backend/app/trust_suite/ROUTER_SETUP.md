# Router Setup for Trust Suite

To register the trust suite router in `main.py`, add the following lines:

```python
# In main.py, add this import:
from app.trust_suite.router import router as trust_router

# Then include the router with the standard /api/v1 prefix:
app.include_router(trust_router, prefix="/api/v1")
```

The router defines its own prefix as `/trust`, so with the `/api/v1` prefix the endpoints will be available at:
- `/api/v1/trust/sets` (POST, GET)
- `/api/v1/trust/sets/mine` (GET)
- `/api/v1/trust/sets/{doc_set_id}` (GET)
- `/api/v1/trust/sets/{doc_set_id}/seller-view` (GET)
- `/api/v1/trust/admin/queue` (GET)
- `/api/v1/trust/admin/review/{queue_id}` (GET)
- `/api/v1/trust/admin/review/{queue_id}/checklist` (PUT)
- `/api/v1/trust/admin/review/{queue_id}/decision` (POST)
- `/api/v1/trust/documents/{document_id}/download` (GET)
- `/api/v1/trust/properties/{property_id}/verification` (GET)