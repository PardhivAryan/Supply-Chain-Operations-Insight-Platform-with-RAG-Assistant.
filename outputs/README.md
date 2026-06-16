# Outputs Folder

This folder stores generated analytics artifacts:

- `business_kpi_summary.json`
- `generated_business_report.md`
- `rag_documents/`

Large cleaned row-level data is ignored by Git and can be regenerated with:

```bash
python manage.py process_supply_chain_data
```
