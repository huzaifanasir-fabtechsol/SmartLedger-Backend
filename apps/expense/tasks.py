from celery import shared_task
from django.conf import settings

from apps.expense.bulk_import import process_import_job


@shared_task(
    name='expense.run_expense_import',
    soft_time_limit=settings.EXPENSE_IMPORT_TIME_LIMIT - 30,
    time_limit=settings.EXPENSE_IMPORT_TIME_LIMIT,
)
def run_expense_import(job_id):
    process_import_job(job_id)
