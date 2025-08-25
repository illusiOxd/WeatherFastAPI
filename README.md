# Weather Forecast API

A RESTful API built with FastAPI that provides real-time weather forecasts and includes a secure user authentication system using JSON Web Tokens (JWT). The application connects to a MongoDB database to manage user data and store weather forecast records.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [API Endpoints](#api-endpoints)
- [Authentication](#authentication)
- [Project Structure](#project-structure)
- [Future Enhancements](#future-enhancements)
- [License](#license)

## Features

- **🔐 Secure Authentication**: User authentication powered by JWT tokens, with bcrypt for password hashing
- **📧 Email Verification**: A secure registration process that uses a one-time password (OTP) sent to the user's email
- **🌤️ Weather Data**: Fetches real-time weather data from the OpenWeatherMap API
- **💾 Data Persistence**: Stores user details and past weather queries in a MongoDB database
- **⚡ Scalable Framework**: Built on FastAPI, known for its high performance and robust features

## Requirements

To run this project, you need to have the following installed:

- Python 3.7+
- MongoDB

The Python dependencies can be installed using pip. It is highly recommended to use a virtual environment.

```bash
pip install fastapi "uvicorn[standard]" pymongo python-jose[jwt] requests bcrypt
```

## Installation

Follow these steps to get the project up and running on your local machine.

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/your-repo-name.git
cd your-repo-name
```

### 2. Create a virtual environment (optional but recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note**: You may need to create a `requirements.txt` file from the list above.

### 4. Set up environment variables

Your code imports sensitive information (database URI, API keys, etc.) from `keys.gitignorfile.py`. For a public repository, a more secure and standard approach is to use a `.env` file.

Create a file named `.env` in the root of your project and populate it with your credentials:

```env
# Example .env file
URI="mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority"
API_KEY="your_openweathermap_api_key"
HOST="127.0.0.1"
PORT="8000"
SECRET_KEY="your_secret_key"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 5. Run the application

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## API Endpoints

The API is structured with the following endpoints.

### Root

A simple health check to ensure the server is running.

- **Method**: `GET`
- **Path**: `/`
- **Description**: Returns the server status
- **Response**:
  ```json
  {
    "server_status": "working"
  }
  ```

### Register

Initiates the registration process by sending an OTP to the user's email.

- **Method**: `POST`
- **Path**: `/register`
- **Description**: Sends a one-time password (OTP) to the provided email address
- **Request Body**:
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Response**:
  ```json
  {
    "message": "OTP sent to your email"
  }
  ```

### Verify OTP and Complete Registration

Verifies the OTP and, if valid, creates a new user and issues a JWT token.

- **Method**: `POST`
- **Path**: `/verify_otp`
- **Description**: Verifies the OTP and completes the user registration
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "your_secure_password",
    "otpcode": "123456"
  }
  ```
- **Response**:
  ```json
  {
    "access_token": "your_jwt_token_here",
    "token_type": "bearer"
  }
  ```

### Get Weather Forecast

A protected endpoint that requires a valid JWT token.

- **Method**: `GET`
- **Path**: `/forecast/{city}`
- **Description**: Fetches weather data for a specified city
- **Request Headers**:
  ```
  Authorization: Bearer <your_jwt_token>
  ```
- **Response**:
  ```json
  {
    "city": "London",
    "status": "sent to mongodb",
    "temperature": 15.5,
    "condition": "scattered clouds"
  }
  ```

## Authentication

This API uses a JWT-based authentication system. The current flow is a single-step registration and token issuance process.

1. **Register**: A user sends a `POST` request to `/register` with their email
2. **Verify & Get Token**: The user then sends a `POST` request to `/verify_otp` with their email, password, and the received OTP. If successful, the API returns a JWT token
3. **Access Protected Endpoints**: This token can then be used in the Authorization header with the Bearer scheme to access protected endpoints like `/forecast/{city}`

## Project Structure

```
.
├── main.py                    # Main FastAPI application file
├── pydantic_models/           # Pydantic models for data validation
│   ├── auth_models.py
│   └── __init__.py
├── services/                  # Service functions like email sending
│   ├── smtp_service.py
│   └── __init__.py
├── functions/                 # Helper functions, e.g., for JWT creation
│   └── jwtfuncs.py
├── keys/                      # Directory for configuration (best to use .env)
│   └── gitignorfile.py        # Your private configuration file
└── README.md
```

## Future Enhancements

- **Add a `/login` endpoint**: Currently, there is no way for a user to get a new token after their initial registration without going through the registration process again. An endpoint for logging in with email and password would be a crucial improvement

- **User Roles**: Expand the role field in the user document to support different user types with varying access levels

- **Error Handling**: Implement more specific error handling for API failures (e.g., city not found, database connection errors)

- **Token Refresh**: Add a token refresh mechanism to provide new tokens without requiring a full re-login

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
