# 🏥 Hospital Management System with Online Self-Appointment Booking

A modern, full‑stack web application that replaces traditional paper‑based hospital workflows. Patients can register, view doctor profiles, and book/cancel appointments online. Doctors manage their availability and schedules. Admins oversee doctors, patients, appointments, and system settings.

## 🚀 Features

### 👤 Patient Portal
- Register / login with email + password  
- Browse doctors (name, specialty)  
- View **real‑time available time slots** (only free slots shown)  
- Book, cancel (≥2 hours before slot), or reschedule appointments  
- See upcoming, past, and cancelled appointments  
- Receive email confirmations & cancellations  

### 👨‍⚕️ Doctor Portal
- Secure login  
- View daily/weekly schedule of own appointments  
- Mark appointments as completed or no‑show  
- Add, remove, or block personal time slots (dynamic intervals)  
- View patient details for each appointment  

### 🛠️ Admin Panel
- Add, edit, delete doctors (assign specialties)  
- View, enable/disable patient accounts  
- See all appointments system‑wide (filters by date, doctor, status)  
- Generate reports: appointment volume, no‑show rate, per‑doctor stats  
- Configure global settings: cancellation window, slot duration, lead days  

### 📅 Appointment Core
- Time‑based slots (e.g., 30‑minute intervals, 9 AM – 5 PM)  
- Double‑booking prevention (real‑time check on backend)  
- Unique appointment ID + email confirmation  
- Cancellation window & booking lead days configurable  

## 🛠️ Tech Stack

| Layer       | Technology                                                                 |
|-------------|----------------------------------------------------------------------------|
| Backend     | Flask (Python)                                                             |
| Frontend    | HTML5, Bootstrap 5, vanilla JavaScript                                    |
| Database    | SQLite (development) / PostgreSQL (production)                            |
| ORM         | SQLAlchemy                                                                 |
| Auth        | Flask‑Login + bcrypt password hashing                                      |
| Emails      | Flask‑Mail (SMTP)                                                          |
| Forms       | Flask‑WTF, WTForms                                                         |
| Environment | python‑dotenv                                                              |

## 📁 Project Structure
