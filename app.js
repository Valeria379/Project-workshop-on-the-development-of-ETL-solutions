

require('dotenv').config();
const express = require('express');
const redis = require('redis');

const app = express();
const port = 3000;

const client = redis.createClient({
  url: 'redis://redis:6379'
});

redisClient.connect().catch(console.error);

// Генерация тестовых данных
async function generateTestData() {
  const testData = [
    { id: 1, name: 'Товар 1', category: 'Электроника', views: 120 },
    { id: 2, name: 'Товар 2', category: 'Одежда', views: 80 },
    { id: 3, name: 'Товар 3', category: 'Бытовая техника', views: 50 }
  ];

  for (const item of testData) {
    await redisClient.set(`/product:${item.id}`, JSON.stringify(item));
  }
  console.log('Тестовые данные загружены в Redis!');
}

// Загружаем тестовые данные при старте
redisClient.on('connect', () => {
  console.log('Подключено к Redis');
  generateTestData();
});

app.get('/', (req, res) => {
  res.send('<h1>Добро пожаловать в систему рекомендаций!</h1><p>Перейдите на <a href="/metrics">/metrics</a> для просмотра метрик.</p>');
});

app.get('/metrics', async (req, res) => {
  try {
    const keys = await redisClient.keys('product:*');
    const metrics = {};

    for (const key of keys) {
      const data = await redisClient.get(key);
      metrics[key] = JSON.parse(data);
    }

    res.json({
      message: 'Текущие данные и метрики',
      metrics
    });
  } catch (err) {
    res.status(500).json({ error: 'Ошибка при получении метрик', details: err.message });
  }
});

app.listen(port, () => {
  console.log(`Сервер запущен на http://localhost:${port}`);
});


