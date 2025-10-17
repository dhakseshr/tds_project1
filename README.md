---
title: Llm Code Deployment
emoji: 🚀
colorFrom: red
colorTo: indigo
sdk: docker
pinned: false
license: mit
---

# LLM Code Deployment Project

This project is a web service that automates the creation and deployment of web applications. It listens for an API request containing a "brief" (a description of the desired web app), uses an AI model to generate the code, and then automatically pushes the new application to a GitHub repository with GitHub Pages enabled.

## Core Technologies

* **FastAPI**: For creating the web server and API endpoint.
* **OpenAI API**: To generate the application code and README file.
* **PyGithub**: To interact with the GitHub API for repository creation and file management.
* **Docker**: For containerizing the application for deployment on Hugging Face Spaces.

## How to Run Locally

1.  Create a Python virtual environment.
2.  Install all dependencies from the `requirements.txt` file:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the application server using Uvicorn:
    ```bash
    uvicorn app.main:app --reload
    ```