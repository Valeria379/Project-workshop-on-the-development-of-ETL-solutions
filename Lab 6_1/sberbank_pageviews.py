# """
# Documentation of pageview format: https://wikitech.wikimedia.org/wiki/Analytics/Data_Lake/Traffic/Pageviews
# """

from urllib import request
from datetime import datetime, timedelta

import airflow.utils.dates
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator

import pendulum  

# Устанавливаем дату начала на 2 месяца назад
start_date = datetime(2025, 2, 1)  # Пример: сбор данных с 1 февраля 2025

dag = DAG(
    dag_id="sberbank_pageviews",
    start_date=start_date,
    schedule_interval="@daily",  # Ежедневный запуск для сбора данных за день
    template_searchpath="/tmp",
    max_active_runs=1,
    catchup=True,  # Обработка пропущенных интервалов за 2 месяца
)


def _get_data(execution_date_str, output_path):
    # Преобразуем строку в объект datetime с учетом временной зоны
    execution_date = pendulum.parse(execution_date_str)
    formatted_date = execution_date.strftime("%Y-%m-%d")
    
    # Формируем URL для Sberbank
    url = (
        f"https://api.sberbank-analytics.ru/pageviews/"
        f"{formatted_date}/sberbank_views.csv.gz"
    )
    request.urlretrieve(url, output_path)

get_data = PythonOperator(
    task_id="get_data",
    python_callable=_get_data,
    op_kwargs={
        "execution_date_str": "{{ logical_date }}",  # Используем logical_date вместо устаревшего execution_date
        "output_path": "/tmp/sberbank_views.gz",
    },
    dag=dag,
)

extract_gz = BashOperator(
    task_id="extract_gz", 
    bash_command="gunzip --force /tmp/sberbank_views.gz", 
    dag=dag
)


def _fetch_pageviews(execution_date):
    target_pages = {"home", "loans", "investments", "cards", "support"}
    result = dict.fromkeys(target_pages, 0)
    
    with open("/tmp/sberbank_views", "r") as f:
        for line in f:
            page, views = line.strip().split(",")
            if page in target_pages:
                result[page] = int(views)
    
    # Сохраняем данные в SQL-файл
    with open("/tmp/postgres_query.sql", "w") as f:
        for page, views in result.items():
            f.write(
                f"INSERT INTO sberbank_pageviews VALUES ("
                f"'{page}', {views}, '{execution_date}'"
                ");\n"
            )


fetch_pageviews = PythonOperator(
    task_id="fetch_pageviews",
    python_callable=_fetch_pageviews,
    op_kwargs={"execution_date": "{{ execution_date }}"},
    dag=dag,
)

write_to_postgres = PostgresOperator(
    task_id="write_to_postgres",
    postgres_conn_id="my_postgres",
    sql="postgres_query.sql",
    dag=dag,
)

get_data >> extract_gz >> fetch_pageviews >> write_to_postgres