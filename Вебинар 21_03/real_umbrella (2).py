import airflow
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import requests
import pandas as pd
from sklearn.linear_model import LinearRegression
import joblib
import os
import random
from datetime import datetime, timedelta

# Настройки DAG
default_args = {
    'owner': 'airflow',
    'start_date': days_ago(1),
}

dag = DAG(
    dag_id="real_umbrella_containerized",
    default_args=default_args,
    description="Fetch weather/sales data, clean, join, train ML model, deploy.",
    schedule_interval="@daily",
)

# 1. Получение прогноза погоды за 30 дней
def fetch_weather_forecast():
    api_key = "459896bfd25b40488c9110037252103"  # замените на ваш API ключ
    url = f"https://api.weatherapi.com/v1/forecast.json?key={api_key}&q=New York&days=30"  # Запрос данных за 30 дней
    response = requests.get(url)
    data = response.json()
    forecast_data = [(day['date'], day['day']['avgtemp_c']) for day in data['forecast']['forecastday']]
    df = pd.DataFrame(forecast_data, columns=['date', 'temperature'])
    data_dir = '/opt/airflow/data'
    os.makedirs(data_dir, exist_ok=True)
    df.to_csv(os.path.join(data_dir, 'weather_forecast.csv'), index=False)
    print("Weather forecast data saved.")

# 2. Очистка данных погоды
def clean_weather_data():
    data_dir = '/opt/airflow/data'
    df = pd.read_csv(os.path.join(data_dir, 'weather_forecast.csv'))
    df['temperature'] = df['temperature'].fillna(method='ffill')
    df.to_csv(os.path.join(data_dir, 'clean_weather.csv'), index=False)
    print("Cleaned weather data saved.")

# 3. Генерация 500 строк данных продаж
def fetch_sales_data():
    # Генерация 500 строк данных
    start_date = datetime(2025, 3, 1)
    sales_data = {
        'date': [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(500)],
        'sales': [random.randint(50, 300) for _ in range(500)]  # Случайные значения продаж от 50 до 300
    }
    df = pd.DataFrame(sales_data)
    data_dir = '/opt/airflow/data'
    os.makedirs(data_dir, exist_ok=True)
    df.to_csv(os.path.join(data_dir, 'sales_data.csv'), index=False)
    print("Sales data saved.")

# 4. Очистка данных продаж
def clean_sales_data():
    data_dir = '/opt/airflow/data'
    df = pd.read_csv(os.path.join(data_dir, 'sales_data.csv'))
    df['sales'] = df['sales'].fillna(method='ffill')
    df.to_csv(os.path.join(data_dir, 'clean_sales.csv'), index=False)
    print("Cleaned sales data saved.")

# 5. Объединение данных
def join_datasets():
    data_dir = '/opt/airflow/data'
    weather_df = pd.read_csv(os.path.join(data_dir, 'clean_weather.csv'))
    sales_df = pd.read_csv(os.path.join(data_dir, 'clean_sales.csv'))
    joined_df = pd.merge(weather_df, sales_df, on='date', how='inner')
    joined_df.to_csv(os.path.join(data_dir, 'joined_data.csv'), index=False)
    print("Joined dataset saved.")

# 6. Обучение ML модели
def train_ml_model():
    data_dir = '/opt/airflow/data'
    df = pd.read_csv(os.path.join(data_dir, 'joined_data.csv'))
    X = df[['temperature']]
    y = df['sales']
    model = LinearRegression()
    model.fit(X, y)
    joblib.dump(model, os.path.join(data_dir, 'ml_model.pkl'))
    print("ML model trained and saved.")

# 7. "Развёртывание" модели
def deploy_ml_model():
    data_dir = '/opt/airflow/data'
    model = joblib.load(os.path.join(data_dir, 'ml_model.pkl'))
    print("Model deployed:", model)

# Операторы
fetch_weather_task = PythonOperator(
    task_id="fetch_weather_forecast",
    python_callable=fetch_weather_forecast,
    dag=dag,
)

clean_forecast_task = PythonOperator(
    task_id="clean_weather_data",
    python_callable=clean_weather_data,
    dag=dag,
)

fetch_sales_task = PythonOperator(
    task_id="fetch_sales_data",
    python_callable=fetch_sales_data,
    dag=dag,
)

clean_sales_task = PythonOperator(
    task_id="clean_sales_data",
    python_callable=clean_sales_data,
    dag=dag,
)

join_datasets_task = PythonOperator(
    task_id="join_datasets",
    python_callable=join_datasets,
    dag=dag,
)
train_ml_model_task = PythonOperator(
    task_id="train_ml_model",
    python_callable=train_ml_model,
    dag=dag,
)

deploy_ml_model_task = PythonOperator(
    task_id="deploy_ml_model",
    python_callable=deploy_ml_model,
    dag=dag,
)

# Зависимости
fetch_weather_task >> clean_forecast_task
fetch_sales_task >> clean_sales_task
[clean_forecast_task, clean_sales_task] >> join_datasets_task
join_datasets_task >> train_ml_model_task >> deploy_ml_model_task