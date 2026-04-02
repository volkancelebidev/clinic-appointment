"""
clinic_appointment.py

A lightweight clinic appointment management system backed by SQLite.

This module exposes three domain models (Doctor, Patient, Appointment) and a
single database-access class (ClinicDB) that follows the Repository pattern —
keeping persistence logic separate from business logic.

Typical usage:
    db = ClinicDB("clinic.db")
    db.add_doctor(Doctor("D001", "Dr. Smith", "Cardiology", 10))
    doctors = db.get_all_doctors()
    db.export_csv("appointments.csv")
"""

import csv
import json
import sqlite3
from datetime import datetime


# ---------------------------------------------------------------------------
# Domain Models
# ---------------------------------------------------------------------------


class Doctor:
    """Represents a physician registered in the clinic.

    Attributes:
        doctor_id:  Unique identifier used as PRIMARY KEY in the database.
        name:       Full name including title (e.g. "Dr. Jane Smith").
        specialty:  Medical specialty (e.g. "Cardiology", "Neurology").
        experience: Years of professional practice.
    """

    def __init__(
        self,
        doctor_id: str,
        name: str,
        specialty: str,
        experience: int,
    ) -> None:
        self.doctor_id = doctor_id
        self.name = name
        self.specialty = specialty
        self.experience = experience

    def __repr__(self) -> str:
        return (
            f"Doctor(id={self.doctor_id!r}, name={self.name!r}, "
            f"specialty={self.specialty!r}, experience={self.experience})"
        )


class Patient:
    """Represents a patient registered in the clinic.

    BMI and risk classification are computed as read-only properties so that
    callers always receive a value consistent with the current weight/height
    without having to call a separate method.

    Attributes:
        patient_id: Unique identifier used as PRIMARY KEY in the database.
        name:       Full name of the patient.
        age:        Age in years.
        weight:     Body weight in kilograms.
        _height:    Height in centimetres (private; use the bmi property).
    """

    # BMI thresholds defined as class-level constants so they can be updated
    # in a single place if clinical guidelines change.
    _BMI_HIGH_THRESHOLD   = 30.0
    _BMI_MEDIUM_THRESHOLD = 25.0

    def __init__(
        self,
        patient_id: str,
        name: str,
        age: int,
        weight: float,
        height: float,
    ) -> None:
        self.patient_id = patient_id
        self.name       = name
        self.age        = age
        self.weight     = weight
        self._height    = height  # Underscore signals internal use; exposed via bmi.

    @property
    def bmi(self) -> float:
        """Body Mass Index calculated from current weight and height.

        Formula: weight(kg) / height(m)^2
        Rounded to one decimal place for display purposes.
        """
        height_m = self._height / 100
        return round(self.weight / (height_m ** 2), 1)

    @property
    def risk_level(self) -> str:
        """Clinical risk classification based on BMI.

        Returns:
            "High"   — BMI >= 30 (obese range)
            "Medium" — BMI >= 25 (overweight range)
            "Normal" — BMI <  25
        """
        if self.bmi >= self._BMI_HIGH_THRESHOLD:
            return "High"
        if self.bmi >= self._BMI_MEDIUM_THRESHOLD:
            return "Medium"
        return "Normal"

    def __repr__(self) -> str:
        return (
            f"Patient(id={self.patient_id!r}, name={self.name!r}, "
            f"age={self.age}, bmi={self.bmi}, risk={self.risk_level!r})"
        )


class Appointment:
    """Represents a scheduled visit linking a patient to a doctor.

    Attributes:
        appt_id:    Unique identifier used as PRIMARY KEY in the database.
        patient_id: Foreign key referencing patients.patient_id.
        doctor_id:  Foreign key referencing doctors.doctor_id.
        date:       Scheduled date/time in "YYYY-MM-DD HH:MM" format.
        status:     One of VALID_STATUSES; defaults to "Pending".
    """

    VALID_STATUSES = ("Pending", "Completed", "Cancelled")

    def __init__(
        self,
        appt_id: str,
        patient_id: str,
        doctor_id: str,
        date: str,
        status: str = "Pending",
    ) -> None:
        if status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid status {status!r}. Must be one of {self.VALID_STATUSES}."
            )
        self.appt_id    = appt_id
        self.patient_id = patient_id
        self.doctor_id  = doctor_id
        self.date       = date
        self.status     = status

    def __repr__(self) -> str:
        return (
            f"Appointment(id={self.appt_id!r}, patient={self.patient_id!r}, "
            f"doctor={self.doctor_id!r}, date={self.date!r}, status={self.status!r})"
        )


# ---------------------------------------------------------------------------
# Database Access — Repository Pattern
# ---------------------------------------------------------------------------


class ClinicDB:
    """Manages all SQLite persistence for the clinic application.

    Implements the Repository pattern: domain models (Doctor, Patient,
    Appointment) contain only business logic, while ClinicDB owns every
    SQL statement.  Swapping the database engine in the future requires
    changes only inside this class.

    Args:
        db_path: Filesystem path to the SQLite file.
                 Defaults to "clinic.db" in the current working directory.

    Example:
        db = ClinicDB("clinic.db")
        db.add_patient(Patient("P001", "Alice", 30, 65.0, 170.0))
    """

    def __init__(self, db_path: str = "clinic.db") -> None:
        self.db_path = db_path
        self._setup_schema()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        """Return a new connection with foreign-key enforcement enabled.

        Foreign keys are OFF by default in SQLite and must be switched on
        per connection.  Centralising this in one helper ensures no
        connection is ever opened without the constraint active.
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _setup_schema(self) -> None:
        """Create (or recreate) the database schema.

        Uses executescript() so that the PRAGMA runs in autocommit mode
        outside any implicit transaction — a requirement for SQLite to
        honour the foreign_keys directive reliably.

        Tables are dropped and recreated on each startup.  In a
        production system you would use migrations instead; for a
        learning project this guarantees a clean, consistent schema.

        Drop order matters: the dependent table (appointments) must be
        removed before the tables it references (patients, doctors).
        """
        with self._connect() as conn:
            conn.executescript("""
                PRAGMA foreign_keys = ON;

                DROP TABLE IF EXISTS appointments;
                DROP TABLE IF EXISTS patients;
                DROP TABLE IF EXISTS doctors;

                CREATE TABLE doctors (
                    doctor_id   TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    specialty   TEXT NOT NULL,
                    experience  INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE patients (
                    patient_id  TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    age         INTEGER NOT NULL,
                    weight      REAL    NOT NULL,
                    height      REAL    NOT NULL
                );

                CREATE TABLE appointments (
                    appt_id     TEXT PRIMARY KEY,
                    patient_id  TEXT NOT NULL REFERENCES patients(patient_id),
                    doctor_id   TEXT NOT NULL REFERENCES doctors(doctor_id),
                    appt_date   TEXT NOT NULL,
                    status      TEXT NOT NULL DEFAULT 'Pending'
                );
            """)

    # ------------------------------------------------------------------
    # Doctor operations
    # ------------------------------------------------------------------

    def add_doctor(self, doctor: Doctor) -> None:
        """Persist a Doctor to the database.

        INSERT OR IGNORE silently skips the row if the primary key already
        exists, making this method safe to call multiple times with the
        same object (idempotent).

        Args:
            doctor: A Doctor instance to persist.
        """
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO doctors (doctor_id, name, specialty, experience)
                VALUES (?, ?, ?, ?)
                """,
                (doctor.doctor_id, doctor.name, doctor.specialty, doctor.experience),
            )

    def get_all_doctors(self) -> list[Doctor]:
        """Return all doctors ordered alphabetically by name.

        Returns:
            A list of Doctor instances; empty list if none exist.
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT doctor_id, name, specialty, experience FROM doctors ORDER BY name"
            ).fetchall()
        return [Doctor(r[0], r[1], r[2], r[3]) for r in rows]

    # ------------------------------------------------------------------
    # Patient operations
    # ------------------------------------------------------------------

    def add_patient(self, patient: Patient) -> None:
        """Persist a Patient to the database.

        Args:
            patient: A Patient instance to persist.
        """
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO patients (patient_id, name, age, weight, height)
                VALUES (?, ?, ?, ?, ?)
                """,
                (patient.patient_id, patient.name, patient.age,
                 patient.weight, patient._height),
            )

    def get_patient(self, patient_id: str) -> Patient | None:
        """Retrieve a single patient by primary key.

        Args:
            patient_id: The patient's unique identifier.

        Returns:
            A Patient instance, or None if no matching record exists.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT patient_id, name, age, weight, height FROM patients WHERE patient_id = ?",
                (patient_id,),
            ).fetchone()

        if row is None:
            return None
        return Patient(row[0], row[1], row[2], row[3], row[4])

    def get_all_patients(self) -> list[Patient]:
        """Return all patients ordered alphabetically by name.

        Returns:
            A list of Patient instances; empty list if none exist.
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT patient_id, name, age, weight, height FROM patients ORDER BY name"
            ).fetchall()
        return [Patient(r[0], r[1], r[2], r[3], r[4]) for r in rows]

    # ------------------------------------------------------------------
    # Appointment operations
    # ------------------------------------------------------------------

    def add_appointment(self, appointment: Appointment) -> None:
        """Persist an Appointment to the database.

        The INSERT is wrapped inside the connection's implicit transaction.
        If the execute raises (e.g. a foreign-key violation), the context
        manager rolls back automatically — the database is never left in a
        partial state.

        Args:
            appointment: An Appointment instance to persist.

        Raises:
            sqlite3.IntegrityError: If patient_id or doctor_id do not exist.
        """
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO appointments (appt_id, patient_id, doctor_id, appt_date, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (appointment.appt_id, appointment.patient_id, appointment.doctor_id,
                 appointment.date, appointment.status),
            )

    def update_appointment_status(self, appt_id: str, new_status: str) -> None:
        """Update the status of an existing appointment.

        Args:
            appt_id:    The appointment's unique identifier.
            new_status: Must be one of Appointment.VALID_STATUSES.

        Raises:
            ValueError: If new_status is not a recognised value.
        """
        if new_status not in Appointment.VALID_STATUSES:
            raise ValueError(
                f"Invalid status {new_status!r}. Must be one of {Appointment.VALID_STATUSES}."
            )
        with self._connect() as conn:
            conn.execute(
                "UPDATE appointments SET status = ? WHERE appt_id = ?",
                (new_status, appt_id),
            )

    def get_all_appointments(self) -> list[dict]:
        """Return all appointments joined with patient and doctor details.

        Uses INNER JOIN across all three tables so each row contains the
        human-readable names rather than raw foreign-key IDs.  Ordered
        chronologically by appointment date.

        Returns:
            A list of dicts with keys: appt_id, patient, doctor,
            specialty, date, status.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    a.appt_id,
                    p.name      AS patient,
                    d.name      AS doctor,
                    d.specialty,
                    a.appt_date AS date,
                    a.status
                FROM appointments a
                INNER JOIN patients p ON a.patient_id = p.patient_id
                INNER JOIN doctors  d ON a.doctor_id  = d.doctor_id
                ORDER BY a.appt_date
                """
            ).fetchall()

        keys = ("appt_id", "patient", "doctor", "specialty", "date", "status")
        return [dict(zip(keys, row)) for row in rows]

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_specialty_stats(self) -> list[dict]:
        """Aggregate appointment counts and completion rates by specialty.

        CASE/WHEN is used inside SUM() to count only rows where status is
        'Completed', avoiding a second query or a Python-side filter loop.

        Returns:
            A list of dicts ordered by total appointments descending,
            with keys: specialty, total, completed, completion_rate.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    d.specialty,
                    COUNT(*)                                                              AS total,
                    SUM(CASE WHEN a.status = 'Completed' THEN 1 ELSE 0 END)              AS completed,
                    ROUND(
                        SUM(CASE WHEN a.status = 'Completed' THEN 1.0 ELSE 0 END)
                        / COUNT(*) * 100,
                        1
                    )                                                                     AS completion_rate
                FROM appointments a
                INNER JOIN doctors d ON a.doctor_id = d.doctor_id
                GROUP BY d.specialty
                ORDER BY total DESC
                """
            ).fetchall()

        return [
            {
                "specialty":       r[0],
                "total":           r[1],
                "completed":       r[2],
                "completion_rate": r[3],
            }
            for r in rows
        ]

    def get_high_risk_patients(self) -> list[dict]:
        """Return patients whose BMI indicates obesity (>= 30).

        BMI is computed inside the SQL query to avoid loading every patient
        into memory just to filter them in Python.  The formula is:
            weight / (height_in_metres ^ 2)

        Returns:
            A list of dicts ordered by BMI descending,
            with keys: patient_id, name, age, bmi.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    patient_id,
                    name,
                    age,
                    ROUND(weight / ((height / 100.0) * (height / 100.0)), 1) AS bmi
                FROM patients
                WHERE (weight / ((height / 100.0) * (height / 100.0))) >= 30
                ORDER BY bmi DESC
                """
            ).fetchall()

        return [
            {"patient_id": r[0], "name": r[1], "age": r[2], "bmi": r[3]}
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_csv(self, filename: str = "appointments.csv") -> None:
        """Write all appointments (with joined details) to a CSV file.

        DictWriter infers column headers from the dict keys, so the output
        format stays in sync with get_all_appointments() automatically.

        Args:
            filename: Destination file path. Defaults to "appointments.csv".
        """
        appointments = self.get_all_appointments()

        if not appointments:
            print("[WARN] No appointments to export.")
            return

        with open(filename, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(appointments[0].keys()))
            writer.writeheader()
            writer.writerows(appointments)

        print(f"[OK] Exported {len(appointments)} appointments to '{filename}'.")

    def export_json(self, filename: str = "statistics.json") -> None:
        """Write analytics data to a JSON file.

        ensure_ascii=False preserves non-ASCII characters (accented names,
        special symbols) without escaping them as \\uXXXX sequences.

        Args:
            filename: Destination file path. Defaults to "statistics.json".
        """
        payload = {
            "generated_at":    datetime.now().strftime("%Y-%m-%d %H:%M"),
            "specialty_stats": self.get_specialty_stats(),
            "high_risk":       self.get_high_risk_patients(),
        }

        with open(filename, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)

        print(f"[OK] Statistics exported to '{filename}'.")

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def health_check(self) -> None:
        """Print a summary of current database record counts.

        In a production system this information would typically be exposed
        as a /health endpoint (HTTP 200 / 503) consumed by a monitoring
        tool such as Prometheus or Datadog.
        """
        with self._connect() as conn:
            doctor_count  = conn.execute("SELECT COUNT(*) FROM doctors").fetchone()[0]
            patient_count = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
            appt_count    = conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
            pending_count = conn.execute(
                "SELECT COUNT(*) FROM appointments WHERE status = 'Pending'"
            ).fetchone()[0]

        separator = "=" * 46
        print(f"\n{separator}")
        print("  SYSTEM STATUS")
        print(separator)
        print(f"  Registered Doctors     : {doctor_count}")
        print(f"  Registered Patients    : {patient_count}")
        print(f"  Total Appointments     : {appt_count}")
        print(f"  Pending Appointments   : {pending_count}")
        print(separator)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Seed the database with sample data and demonstrate all operations."""

    print("[+] Clinic Appointment Management System — starting\n")

    db = ClinicDB("clinic.db")

    # --- Doctors -----------------------------------------------------------
    doctors = [
        Doctor("D001", "Dr. Ayse Kara",     "Cardiology",    15),
        Doctor("D002", "Dr. Mehmet Yildiz", "Neurology",      8),
        Doctor("D003", "Dr. Elif Sahin",    "Endocrinology", 12),
        Doctor("D004", "Dr. Can Ozturk",    "Cardiology",     5),
    ]
    for d in doctors:
        db.add_doctor(d)

    print("[Doctors]")
    for d in db.get_all_doctors():
        print(f"  {d}")

    # --- Patients ----------------------------------------------------------
    patients = [
        Patient("H001", "Volkan Celebi", 34,  88.0, 178.0),
        Patient("H002", "Selin Arslan",  45,  95.0, 160.0),
        Patient("H003", "Tarik Demir",   52,  70.0, 175.0),
        Patient("H004", "Zeynep Aktas",  29, 105.0, 162.0),
        Patient("H005", "Burak Gunes",   61,  78.0, 172.0),
    ]
    for p in patients:
        db.add_patient(p)

    print("\n[Patients]")
    for p in db.get_all_patients():
        print(f"  {p}")

    # --- Appointments ------------------------------------------------------
    appointments = [
        Appointment("R001", "H001", "D001", "2026-04-10 09:00", "Completed"),
        Appointment("R002", "H002", "D003", "2026-04-11 10:30", "Completed"),
        Appointment("R003", "H003", "D002", "2026-04-12 14:00", "Pending"),
        Appointment("R004", "H004", "D001", "2026-04-13 11:00", "Pending"),
        Appointment("R005", "H005", "D002", "2026-04-14 15:30", "Cancelled"),
        Appointment("R006", "H001", "D003", "2026-04-15 09:30", "Pending"),
        Appointment("R007", "H002", "D004", "2026-04-16 13:00", "Completed"),
    ]
    for a in appointments:
        db.add_appointment(a)

    # Simulate a status transition: the pending check-up has been completed.
    db.update_appointment_status("R003", "Completed")

    print("\n[Appointments]")
    for a in db.get_all_appointments():
        print(
            f"  [{a['status']:10}] {a['patient']:18} -> "
            f"{a['doctor']:24} ({a['specialty']}) | {a['date']}"
        )

    # --- Analytics ---------------------------------------------------------
    print("\n[Specialty Statistics]")
    for s in db.get_specialty_stats():
        print(
            f"  {s['specialty']:15} | Total: {s['total']} | "
            f"Completed: {s['completed']} | Rate: {s['completion_rate']}%"
        )

    print("\n[High-Risk Patients — BMI >= 30]")
    for p in db.get_high_risk_patients():
        print(f"  {p['name']:18} | Age: {p['age']} | BMI: {p['bmi']}")

    # --- Export & health check ---------------------------------------------
    print()
    db.export_csv("appointments.csv")
    db.export_json("statistics.json")
    db.health_check()


if __name__ == "__main__":
    main()