# Clinic Appointment Management System

A SQLite-backed clinic appointment management system that handles doctor 
and patient registration, appointment scheduling, risk classification, 
and structured reporting.

Built to practice the Repository Pattern, multi-table SQL design, and 
data export pipelines in Python.

---

## Problem It Solves

Clinics managing appointments manually struggle with tracking patient 
risk levels, monitoring completion rates by specialty, and exporting 
structured reports. This system centralises all three in a single 
lightweight application.

---

## Features

- **Doctor & Patient Management** — registration with full CRUD support
- **Appointment Scheduling** — link patients to doctors with status tracking (Pending / Completed / Cancelled)
- **BMI Risk Classification** — automatic High / Medium / Normal assessment per patient
- **Specialty Statistics** — completion rates aggregated by medical specialty via SQL GROUP BY
- **High-Risk Detection** — filters patients with BMI >= 30 directly in SQL
- **CSV & JSON Export** — structured data export with generation timestamp

---

## Tech Stack

| Layer      | Technology                         |
|------------|------------------------------------|
| Language   | Python 3.12                        |
| Database   | SQLite (via built-in sqlite3)      |
| Paradigm   | OOP — Repository Pattern           |
| Export     | CSV, JSON                          |

---

## Project Structure
```
clinic-appointment/
├── clinic_appointment.py    # Domain models + database access + reporting
└── .gitignore
```
---

## How to Run

```bash
git clone https://github.com/volkancelebidev/clinic-appointment.git
cd clinic-appointment
python clinic_appointment.py
```
---

## What I Learned

This project was built to practice and consolidate:
- Designing a multi-table relational schema with FOREIGN KEY constraints
- Separating domain models from database logic using the Repository Pattern
- Writing INNER JOIN queries across three tables in a single statement
- Using CASE/WHEN inside SQL aggregations for conditional counting
- Exporting relational data to both CSV and JSON formats
