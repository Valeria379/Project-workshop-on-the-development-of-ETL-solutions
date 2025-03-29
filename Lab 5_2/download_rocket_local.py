import json
import pathlib
import logging
from datetime import timedelta

import airflow.utils.dates
import requests
import requests.exceptions as requests_exceptions
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator


# Настройка логгера
log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/airflow/logs/rocket_downloader.log'),
        logging.StreamHandler()
    ]
)

dag = DAG(
    dag_id="download_rocket_local",
    description="Download rocket pictures with detailed logging",
    start_date=airflow.utils.dates.days_ago(14),
    schedule_interval="@daily",
    default_args={
        'owner': 'airflow',
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    }
)

def _get_pictures():
    images_dir = "/opt/airflow/data/images"
    pathlib.Path(images_dir).mkdir(parents=True, exist_ok=True)
    
    log.info(f"Starting image download to {images_dir}")
    
    try:
        with open("/opt/airflow/data/launches.json") as f:
            launches = json.load(f)
            image_urls = [launch["image"] for launch in launches["results"]]
            log.info(f"Found {len(image_urls)} images to download")
            
            success_count = 0
            for idx, image_url in enumerate(image_urls, 1):
                try:
                    response = requests.get(image_url, timeout=10)
                    image_filename = image_url.split("/")[-1]
                    target_file = f"{images_dir}/{image_filename}"
                    
                    with open(target_file, "wb") as f:
                        f.write(response.content)
                    
                    log.info(f"[{idx}/{len(image_urls)}] Downloaded {image_filename}")
                    success_count += 1
                    
                except requests_exceptions.MissingSchema:
                    log.warning(f"Invalid URL format: {image_url}")
                except requests_exceptions.ConnectionError:
                    log.error(f"Connection failed for {image_url}")
                except Exception as e:
                    log.error(f"Error downloading {image_url}: {str(e)}")
            
            log.info(f"Download complete. Success: {success_count}/{len(image_urls)}")
            return success_count
            
    except Exception as e:
        log.error(f"Fatal error in _get_pictures: {str(e)}")
        raise

# Изменение пути для скачивания JSON-файла в папку data
download_launches = BashOperator(
    task_id="download_launches",
    bash_command="curl -o /opt/airflow/data/launches.json -L 'https://ll.thespacedevs.com/2.0.0/launch/upcoming'",  # noqa: E501
    dag=dag,
)

def _get_pictures():
    # Обеспечиваем существование директории для изображений в папке data
    images_dir = "/opt/airflow/data/images"
    pathlib.Path(images_dir).mkdir(parents=True, exist_ok=True)

    # Загружаем все картинки из launches.json
    with open("/opt/airflow/data/launches.json") as f:
        launches = json.load(f)
        image_urls = [launch["image"] for launch in launches["results"]]
        for image_url in image_urls:
            try:
                response = requests.get(image_url)
                image_filename = image_url.split("/")[-1]
                target_file = f"{images_dir}/{image_filename}"
                with open(target_file, "wb") as f:
                    f.write(response.content)
                print(f"Downloaded {image_url} to {target_file}")
            except requests_exceptions.MissingSchema:
                print(f"{image_url} appears to be an invalid URL.")
            except requests_exceptions.ConnectionError:
                print(f"Could not connect to {image_url}.")

get_pictures = PythonOperator(
    task_id="get_pictures", python_callable=_get_pictures, dag=dag
)

# Обновляем команду уведомления, чтобы она считала количество изображений в папке data/images
notify = BashOperator(
    task_id="notify",
bash_command='echo "There are now $(ls /opt/airflow/data/images/ | wc -l) images."',
    dag=dag,
)

download_launches >> get_pictures >> notify