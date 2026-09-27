// Нагрузочный тест на /question (k6). Пишется как файл теста, но НЕ запускается автоматически -
// требует полностью поднятого стека (app + Postgres + Chroma) и валидного GEMINI_API_KEY,
// плюс тратит реальные токены LLM на каждый некэшированный вопрос.
//
// Запуск вручную:
//   k6 run tests/stress/question_load_test.js
//   k6 run -e BASE_URL=http://localhost:8000 tests/stress/question_load_test.js
//
// В CI/CD пока сознательно не подключается (см. TODO) - добавим позже отдельным шагом.

import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Небольшой набор вопросов, часть повторяется намеренно - чтобы часть нагрузки
// шла в кэш вопрос-ответ (см. Question.execute), а часть каждый раз считалась заново.
const QUESTIONS = [
  'Где находится деканат?',
  'Когда собирается клуб настольных игр?',
  'Как записаться на пересдачу?',
  'Что такое ИИМРТ?',
  'Где находится деканат?',
];

export const options = {
  scenarios: {
    smoke: {
      executor: 'constant-vus',
      vus: 10,
      duration: '30s',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<5000'],
    http_req_failed: ['rate<0.05'],
  },
};

export default function () {
  const question = QUESTIONS[Math.floor(Math.random() * QUESTIONS.length)];

  const response = http.post(
    `${BASE_URL}/question`,
    JSON.stringify({ question }),
    { headers: { 'Content-Type': 'application/json' } },
  );

  check(response, {
    'status is 200': (r) => r.status === 200,
    'body has answer field': (r) => {
      try {
        return JSON.parse(r.body).answer !== undefined;
      } catch (e) {
        return false;
      }
    },
  });

  sleep(1);
}
