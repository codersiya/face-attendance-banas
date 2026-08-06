# Face Attendance — Employee Enrollment System

FastAPI + React + PostgreSQL (pgvector) system for enrolling employees with
3 face images (front / left / right) and storing their face embeddings
alongside shift and attendance-rule metadata.

## File structure

```
face-attendance-system/
├── docker-compose.yml          # PostgreSQL + pgvector for local dev
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── schema.sql               # reference SQL (auto-created by the app too)
│   └── app/
│       ├── main.py              # FastAPI app entrypoint
│       ├── config.py            # env-based settings
│       ├── database.py          # SQLAlchemy engine/session
│       ├── models.py            # Employee ORM model (int PK, 3 vector cols)
│       ├── schemas.py           # Pydantic request/response models
│       ├── face_service.py      # face detection + embedding generation
│       └── routers/
│           └── employees.py     # create / enroll-faces / list / get / match
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── styles.css
        ├── api/
        │   └── employeeApi.js
        └── components/
            ├── CameraCapture.jsx        # PC webcam + phone camera capture
            └── EmployeeEnrollForm.jsx   # 3-step enrollment wizard
```

## Data model (one row per employee)

| Column                | Type          | Notes                                   |
|------------------------|---------------|------------------------------------------|
| employee_id            | INTEGER PK    | auto-increment SERIAL, **not UUID**       |
| employee_name          | VARCHAR       |                                          |
| department              | VARCHAR       |                                          |
| designation             | VARCHAR       |                                          |
| shift_start_time / shift_end_time | TIME | shift timing                     |
| grace_time_minutes     | INTEGER       | attendance rule                          |
| late_entry_minutes     | INTEGER       | attendance rule                          |
| overtime_rules         | TEXT          | attendance rule (free text)              |
| embedding_front         | VECTOR(128)   | pgvector column                          |
| embedding_left          | VECTOR(128)   | pgvector column                          |
| embedding_right         | VECTOR(128)   | pgvector column                          |
| is_enrolled             | BOOLEAN       | true once all 3 embeddings are stored    |

All three embeddings live as separate columns **on the same employee row**,
as requested — not in a separate child table.

## Backend setup

```bash
cd backend
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start Postgres with pgvector (from repo root)
docker compose up -d

cp .env.example .env      # adjust DATABASE_URL if needed

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The app auto-creates the `vector` extension and the `employees` table on
startup. API docs available at `http://localhost:8000/docs`.

> `face_recognition` depends on `dlib`, which needs CMake + a C++ compiler
> to build. On Ubuntu: `sudo apt-get install -y cmake build-essential`.
> On Windows, installing via `conda install -c conda-forge dlib` is usually
> far less painful than pip.

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5173`. Set `VITE_API_BASE_URL` in a `.env` file
if the backend isn't at `http://localhost:8000`.

**Camera on a phone:** `getUserMedia` (used for both PC webcam and phone
camera capture) requires a secure context. `localhost` is exempt, but
opening the dev server from a phone over your LAN IP needs HTTPS — use a
tunnel (e.g. `ngrok http 5173`) or a reverse proxy with a TLS cert for
real device testing.

## API endpoints

| Method | Path                                   | Purpose                                   |
|--------|-----------------------------------------|--------------------------------------------|
| POST   | `/api/employees`                        | Create employee record (metadata only)     |
| POST   | `/api/employees/{id}/enroll-faces`      | Upload front/left/right images → embeddings|
| GET    | `/api/employees`                        | List all employees                         |
| GET    | `/api/employees/{id}`                   | Get one employee                           |
| PUT    | `/api/employees/{id}`                   | Update employee metadata                   |
| DELETE | `/api/employees/{id}`                   | Delete employee                            |
| POST   | `/api/employees/match`                  | Match a live photo against enrolled faces  |

## Enrollment flow (matches the UI)

1. Admin fills in **Employee Name / Department / Designation / Shift
   timing / Attendance rules** → `POST /api/employees` creates the row and
   returns the integer `employee_id`.
2. Admin captures 3 photos (front, left, right) using the PC webcam or a
   phone's camera via the browser → `POST /api/employees/{id}/enroll-faces`
   sends all 3 as multipart form data.
3. Backend detects exactly one face per image, generates a 128-d embedding
   for each with `face_recognition` (dlib), and stores the three vectors in
   `embedding_front`, `embedding_left`, `embedding_right` on that employee's
   row, setting `is_enrolled = true`.

## Production notes

- Put the API behind HTTPS (required for camera access on non-localhost
  origins) and restrict `ALLOWED_ORIGINS` to your real frontend domain.
- Add authentication/authorization (e.g. JWT) in front of the `employees`
  router before exposing this beyond a trusted admin network — enrollment
  endpoints are unauthenticated in this scaffold.
- For large workforces, replace the Python-side loop in `/match` with a
  pgvector `ORDER BY embedding <-> :probe LIMIT 1` query per column, and add
  an IVFFlat/HNSW index (see `schema.sql`).
- Run schema changes through Alembic migrations rather than relying on
  `Base.metadata.create_all` in production.
