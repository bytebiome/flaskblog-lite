# flaskblog-lite
A light version of a flask-based blog

## Overview
This project is a blog/website built with **Flask**, a lightweight Python framework. This version supports creating posts in **HTML**, managing an image gallery, an administration area, and a convenient **day/night mode** feature for an optimal reading experience.

## Key Features
* **Post Management:** Create, edit, and delete posts directly from the admin area.
* **HTML allowed:** Write your articles using HTML syntax for web formatting.
* **Image Gallery:** Upload and manage images for your posts.
* **User Authentication:** A secure login/logout system for website administration.
* **Theming:** Support for day (light) and night (dark) modes to reduce eye strain.
* **Contact messages:** Receive contact messages, visualize in your dashboard. Read, delete, and mark as read your messages.


## Technologies Used
* **Backend:** [Python](https://www.python.org/) 🐍
    * [Flask](https://flask.palletsprojects.com/)
    * [SQLAlchemy](https://www.sqlalchemy.org/) (for database management)
* **Frontend:**
    * **HTML** / **Jinja2** (for templates)
    * **CSS** (with support for variables and themes)


## Installation and Startup
Follow these steps to run the project locally.

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/your-project-name.git](https://github.com/your-username/your-project-name.git)
    cd your-project-name
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # On macOS/Linux
    python3 -m venv venv
    source venv/bin/activate