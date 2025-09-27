#  Dummy UDM + TMS Unified Portal

This repository contains a **single simulation portal** that provides access to both:  
- **UDM (User Depot Module)** → manages fitting date records.  
- **TMS (Technician Management System)** → manages risk levels.  

It simulates how the **Vendor Site** connects with the official government UDM/TMS systems.  
Whenever data is entered in the Vendor Site, it is **synced with this portal**, which then stores it in its own databases.

---

##  Screenshots

- Unified Home Page (choice between UDM/TMS)  
  ![WhatsApp Image 2025-09-12 at 19 50 06_d34f742b](https://github.com/user-attachments/assets/b60e4b22-973d-4772-93aa-aa953bdefc7c)

- UDM Section (Dashboard)  
  ![WhatsApp Image 2025-09-12 at 19 50 40_26e09a2a](https://github.com/user-attachments/assets/b6af076f-43ce-4752-b7e2-2f09e33ae8a9)

- UDM Section (Analytics)
  ![WhatsApp Image 2025-09-12 at 19 50 57_a33734bd](https://github.com/user-attachments/assets/a113541c-a1fa-4bc8-8a1b-0203e2fef266)

- UDM Section (Vendor Management)
   ![WhatsApp Image 2025-09-12 at 19 51 12_8d850e26](https://github.com/user-attachments/assets/2f9de7e1-e3ee-496e-a08c-d95bcc7437af)

- UDM Section (Inspection)
   ![WhatsApp Image 2025-09-12 at 19 51 28_6335c92a](https://github.com/user-attachments/assets/f4410e03-4cf0-45d2-9944-31089fe94d7d)

- TMS Section  
   ![WhatsApp Image 2025-09-12 at 19 51 47_4b62dc77](https://github.com/user-attachments/assets/cf9324a8-c15f-4958-8ec3-b5abf860debf)

---

##  Data Flow Simulation

1. **Vendor Site Entry**  
   - Vendor enters fitting details.  
   - Data is synced into this Dummy Portal.  

2. **UDM Section**  
   - Stores **date-related info**:  
     - Manufacture Date  
     - Supply Date  
     - Warranty Date  
     - Inspection Date  

3. **TMS Section**  
   - Stores **risk-related info**:  
     - Asset Risk Level  
     - Vendor Risk Level  

---

##  Features

- **Unified Portal** → single entry point for UDM & TMS.  
- **UDM Section** → manages manufacturing, supply, warranty, inspection dates.  
- **TMS Section** → manages technician inspection logs, fitting risk, vendor risk.  
- **Data Sync** → vendor site pushes data here for simulation.  

---

##  Tech Stack

- **Language:** Python 3.10+, HTML, CSS 
- **Framework:** Flask  
- **Database:** SQLite (with UDM and TMS tables)  
- **Visualization:** Chart.js (for analytics)  

---

##  Getting Started

### Prerequisites
- Python 3.10+  
- Flask installed (`pip install flask`)  

### Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/dummy-udm-tms.git
cd dummy-udm-tms

# Install dependencies
pip install -r requirements.txt
```


### Run Locally
```bash
python app.py
```

### Access

- Portal Home: http://localhost:5001

- From here, select either UDM or TMS.

---  
## Project Structure

```bash
udm_tms_demo/
|-_init.py
|-app.py
|-helper.py
|-companion_data.db
|-udm/
|  |-_init.py
|  |-udm.py
|-tms/
|  |-_init.py
|  |-tms.py
|-static/
|   |-azadi.png
|   |-rail.png
|-templates/
    |-all.html
    |-view.html
    |-udm.html
    |-tms.html
```
---
## Future Scope

- Real API integration with government UDM/TMS.

- Authentication + role-based access (vendor/technician).

- Automated alerts based on risk level.

- Digital signatures for inspection records.
  
---
## License

MIT License © 2025 Debanshu2005
