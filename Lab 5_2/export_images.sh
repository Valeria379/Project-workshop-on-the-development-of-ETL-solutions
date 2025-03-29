# Конфигурация
CONTAINER_DATA_PATH="/home/mgpu/Documents/workshop-on-ETL/business_case_rocket_25/data/images"   # Путь к изображениям в контейнере
LOCAL_TARGET_DIR="home/mgpu/Downloads/rocket_images" # Целевая папка

# Копируем файлы
echo "$(date): Копирование изображений из контейнера"
cp -r "$CONTAINER_DATA_PATH"/* "$LOCAL_TARGET_DIR"


# Устанавливаем корректные права
chmod -R 755 "$LOCAL_TARGET_DIR"
echo -e "\nПрава доступа установлены (755)"