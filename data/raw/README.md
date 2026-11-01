# Optional full-data download

The app runs from the included real 12,000-order sample and needs no Kaggle account.

To reproduce the sample:

1. Visit https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce.
2. Use the official Download button. If Kaggle asks you to sign in, sign in yourself; do not paste credentials into the application.
3. Save the official ZIP as data/raw/olist.zip.
4. From the repository root run:
   .venv\Scripts\python.exe scripts\prepare_data.py --archive data\raw\olist.zip
5. Run scripts/train.py again to refresh data-specific model artifacts.

The public endpoint https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce was accessible without authentication on 2026-11-01. Availability may change; use the official page if it requires authentication.

Required source CSVs inside the ZIP: olist_orders_dataset.csv, olist_order_items_dataset.csv, olist_customers_dataset.csv, olist_products_dataset.csv, product_category_name_translation.csv. The script reads allowlisted ZIP entries without extracting arbitrary paths. The raw ZIP and its contents are ignored by Git.