# Wolf Blogs

Wolf Blogs is a Flask + MongoDB blog application with:

- public blog feed with banners and posts
- admin dashboard for managing banners and posts
- user signup and login
- Google authentication for user signup/sign-in
- likes, comments, profile image uploads, and real-time updates with Socket.IO

## Tech Stack

<p align="left">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask" />
  <img src="https://img.shields.io/badge/Socket.IO-010101?style=for-the-badge&logo=socketdotio&logoColor=white" alt="Socket.IO" />
  <img src="https://img.shields.io/badge/MongoDB-47A248?style=for-the-badge&logo=mongodb&logoColor=white" alt="MongoDB" />
  <img src="https://img.shields.io/badge/GridFS-13AA52?style=for-the-badge&logo=mongodb&logoColor=white" alt="GridFS" />
  <img src="https://img.shields.io/badge/Pillow-8CAAE6?style=for-the-badge&logo=python&logoColor=white" alt="Pillow" />
  <img src="https://img.shields.io/badge/Google%20Identity-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Google Identity" />
</p>

## Project Structure

```text
Blog/
├── app.py
├── requirements.txt
├── templates/
├── static/
│   ├── css/
│   ├── js/
│   └── images/
└── venv/
```

## Features

- Homepage with banner slider and blog post cards
- Admin panel for:
  - adding, editing, and deleting banners
  - adding, editing, and deleting posts
- Banner image uploads stored in GridFS
- High-quality banner thumbnail generation
- User authentication with:
  - username/email + password
  - Google signup/sign-in
- Post likes and comments
- Profile image upload
- Real-time UI updates using Socket.IO

## Requirements

- Python 3.13 recommended
- MongoDB Atlas database
- A Google OAuth Web Client ID for Google login

Install Python dependencies:

```powershell
venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Configuration

### 1. MongoDB

This project currently connects using values in [app.py](c:/Code%20Space/Blog/Blog/app.py):

```python
app.config["MONGO_URI"] = "your-mongodb-uri"
app.config["MONGO_DBNAME"] = "BlogDB"
```

Important:

- the app uses the database named `BlogDB`
- collection names are case-sensitive
- the app writes to lowercase collections like `posts`, `banners`, and `users`

If you see data in `Posts` or `Banners`, those are different collections from `posts` and `banners`.

### 2. Google Authentication

Set your Google client ID before starting the app:

```powershell
$env:GOOGLE_CLIENT_ID="your-google-client-id.apps.googleusercontent.com"
```

In Google Cloud Console:

1. Create an OAuth client of type `Web application`
2. Add this JavaScript origin for local development:

```text
http://localhost:5000
```

3. Open the app locally using:

```text
http://localhost:5000
```

Do not use a LAN IP like `http://192.168.x.x:5000` for Google auth during local setup unless that exact origin is allowed and supported by Google.

## Run Locally

Start the app with:

```powershell
venv\Scripts\python.exe app.py
```

Then open:

```text
http://localhost:5000
```

## Default Routes

- `/` - public homepage
- `/user_auth` - user login/signup page
- `/login` - admin login
- `/admin` - admin dashboard

## Database Collections

Main collections used by the app:

- `posts`
- `banners`
- `users`
- `admins`
- `fs.files`
- `fs.chunks`

Notes:

- `fs.files` and `fs.chunks` store uploaded binary files using GridFS
- `posts` and `banners` store the application documents
- post and banner documents reference GridFS file IDs

## Media Storage

- Post attachments are stored in GridFS
- Banner images are stored in GridFS
- Banner thumbnails are generated automatically with Pillow
- Banner thumbnails are optimized for better visual quality on the homepage

## Authentication Notes

### User auth

- manual signup stores `username`, `email`, and `password`
- Google auth verifies the Google ID token server-side
- if the Google account email already exists, the user is logged in
- if it does not exist, a new user is created automatically

### Admin auth

- admin login uses the `admins` collection
- admin session is stored in Flask session data

## Development Notes

- run the app with `socketio.run(...)` via `app.py`
- uploaded files are served through GridFS routes
- banner and post updates are pushed over Socket.IO
- some existing database collections may use old capitalized names like `Posts` or `Banners`; the app uses lowercase collections

## Troubleshooting

### Google login says `origin_mismatch`

Make sure:

- you added `http://localhost:5000` to `Authorized JavaScript origins`
- you opened the app at `http://localhost:5000`
- you did not open it with `127.0.0.1` or a LAN IP unless those exact origins were also configured

### Google button does not appear

Make sure:

- `GOOGLE_CLIENT_ID` is set in the same shell session where you start Flask
- you restarted the app after setting the environment variable

### Atlas does not show inserted posts

Check:

- database: `BlogDB`
- collection: `posts`

Do not confuse:

- `Posts` with `posts`
- `Banners` with `banners`

## Dependencies

Current dependencies are listed in [requirements.txt](c:/Code%20Space/Blog/Blog/requirements.txt):

- Flask
- Flask-SocketIO
- eventlet
- gunicorn
- pymongo
- Werkzeug
- Pillow
- dnspython
- google-auth
- requests

