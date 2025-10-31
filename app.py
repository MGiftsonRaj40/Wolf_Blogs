from flask import (
    Flask, render_template, request, Response,
    redirect, url_for, session, flash, jsonify, send_file
)
from flask_pymongo import PyMongo
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from io import BytesIO
import os
import gridfs
from datetime import datetime, timezone
import mimetypes
from flask_socketio import SocketIO, emit
from PIL import Image
import io

# ----------------- APP SETUP -----------------
app = Flask(__name__)
app.secret_key = "a3f97b2b3c8f5d09d4e87f2f4c3a6b7de"

# IMPORTANT: use SocketIO runner
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

# MongoDB Atlas URI (change if needed)
app.config["MONGO_URI"] = "mongodb+srv://mgiftsonraj04:5OSQIOy0M4bMrScq@cluster1.5qfr84g.mongodb.net/Blog?retryWrites=true&w=majority"
mongo = PyMongo(app)
fs = gridfs.GridFS(mongo.db)

# Upload settings (still kept in case you use local fallback)
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx', 'mp4', 'mkv', 'webm'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ----------------- HELPERS -----------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _ensure_str(obj):
    return str(obj) if obj is not None else None


def serialize_post(post, current_user=None):
    """Serialize post for JSON / frontend consumption"""
    if not post:
        return None

    out = {
        "_id": _ensure_str(post.get("_id")),
        "title": post.get("title", ""),
        "content": post.get("content", ""),
        "likes": post.get("likes", 0),
        "liked_by_current_user": current_user in post.get("likes_users", []) if current_user else False,
        "date": post.get("date").isoformat() if isinstance(post.get("date"), datetime) else str(post.get("date")),
        "files": [
            {
                "file_id": _ensure_str(f.get("file_id")),
                "filename": f.get("filename", ""),
                "type": f.get("type", "document")
            } for f in post.get("files", []) or []
        ],
        "comments": [
            {
                "user_id": _ensure_str(c.get("user_id")),
                "username": c.get("username", "Unknown"),
                "text": c.get("text", ""),
                "date": c.get("date").isoformat() if isinstance(c.get("date"), datetime) else str(c.get("date"))
            } for c in post.get("comments", []) or []
        ]
    }

    return out

def json_safe(doc):
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            doc[k] = str(v)
        elif isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


# ----------------- ROUTES -----------------
@app.route('/')
def index():
    posts_cursor = mongo.db.posts.find()
    banners_cursor = mongo.db.banners.find()

    # ===== POSTS =====
    posts = []
    for p in posts_cursor:
        post = serialize_post(p)
        post["type"] = "post"
        post["datetime"] = p.get("date") or datetime.min
        post["formatted_date"] = p.get("date").strftime("%b %d, %Y") if p.get("date") else ""
        posts.append(post)

    # ===== BANNERS =====
    banners = []  # ← make sure this is defined before appending
    for b in banners_cursor:
        b["_id"] = str(b["_id"])
        b["type"] = "banner"
        b["datetime"] = b.get("created_at") or datetime.min
        b["formatted_date"] = b.get("created_at").strftime("%b %d, %Y") if b.get("created_at") else ""
        if b.get("image"):
            b["image"] = str(b["image"])
        banners.append(b)

    # ===== MERGE + SORT =====
    combined = sorted(posts + banners, key=lambda x: x.get("datetime", datetime.min), reverse=True)

    user = None
    if 'user' in session:
        user = mongo.db.users.find_one({'username': session['user']})

    return render_template('index.html', feed=combined, posts=posts, banners=banners, user=user)

@app.route('/post/<post_id>')
def post_detail(post_id):
    try:
        post = mongo.db.posts.find_one({'_id': ObjectId(post_id)})
    except Exception:
        return "Post not found", 404
    if not post:
        return "Post not found", 404
    return render_template('post_detail.html', post=serialize_post(post))


# ----------------- ADMIN -----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'admin' in session:
        return redirect(url_for('admin'))
    if request.method == 'POST':
        user = mongo.db.admins.find_one({'username': request.form['username']})
        if user and user['password'] == request.form['password']:
            session['admin'] = user['username']
            return redirect(url_for('admin'))
        flash('Invalid credentials')
    return render_template('login.html')


@app.route('/admin')
def admin():
    if 'admin' not in session:
        return redirect(url_for('login'))

    # ===== POSTS =====
    posts_cursor = mongo.db.posts.find().sort('date', -1)
    posts = []
    for p in posts_cursor:
        post = serialize_post(p)
        # Remove image files
        post['files'] = [f for f in post.get('files', []) if f['type'] != 'image']
        # Add datetime and formatted date
        post['datetime'] = p.get('date') or datetime.min
        post['formatted_date'] = p.get('date').strftime("%b %d, %Y") if p.get('date') else ""
        posts.append(post)

    # ===== BANNERS =====
    banners_cursor = mongo.db.banners.find().sort('date', -1)
    banners = []
    for b in banners_cursor:
        banners.append({
            "_id": str(b["_id"]),
            "title": b.get("title", ""),
            "content": b.get("content", ""),
            "tags": b.get("tags", []),
            "datetime": b.get("date") or datetime.min,
            "formatted_date": b.get("date").strftime("%b %d, %Y") if b.get("date") else ""
        })

    return render_template('admin.html', posts=posts, banners=banners)

@app.route('/get_user')
def get_user():
    if 'user' not in session:
        return jsonify({})
    user = mongo.db.users.find_one({'username': session['user']}, {'_id': 0})
    return jsonify(user)

@app.route('/get_post/<post_id>')
def get_post(post_id):
    try:
        post = mongo.db.posts.find_one({'_id': ObjectId(post_id)})
    except Exception:
        return jsonify({"error": "Invalid ID"}), 400
    if not post:
        return jsonify({"error": "Post not found"}), 404
    return jsonify(serialize_post(post))

# ----------------- BANNER ROUTES -----------------
@app.route('/add_banner', methods=['POST'])
def add_banner():
    title = request.form.get('title')
    content = request.form.get('content')
    tags = request.form.get('tags', '').split(',')
    tags = [t.strip() for t in tags if t.strip()]
    file = request.files.get('image')

    file_id = None
    thumb_id = None

    if file:
        file_bytes = io.BytesIO(file.read())
        file_bytes.seek(0)
        file_id = fs.put(file_bytes, filename=file.filename, contentType=file.content_type)

        file_bytes.seek(0)
        img = Image.open(file_bytes)
        img.thumbnail((800, 800))
        temp = io.BytesIO()
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(temp, format='JPEG')
        temp.seek(0)
        thumb_id = fs.put(temp, filename="thumb_" + file.filename, contentType='image/jpeg')


    banner_doc = {
        "title": title,
        "content": content,
        "tags": tags,
        "image": str(file_id) if file_id else None,
        "thumb": str(thumb_id) if thumb_id else None,
        "created_at": datetime.now(timezone.utc)
    }

    inserted = mongo.db.banners.insert_one(banner_doc)
    banner_doc["_id"] = str(inserted.inserted_id)

    # Prepare JSON-serializable data
    banner_doc_serialized = banner_doc.copy()
    banner_doc_serialized["created_at"] = banner_doc_serialized["created_at"].isoformat()

    # Emit to clients
    socketio.emit('new_banner', banner_doc_serialized, namespace='/')

    return jsonify({"success": True, "banner": banner_doc_serialized})

@app.route('/get_banners')
def get_banners():
    banners = []
    for b in mongo.db.banners.find().sort('created_at', -1):  # DESCENDING: newest first
        b['_id'] = str(b['_id'])
        if b.get('image'):
            b['image'] = str(b['image'])
        if b.get('thumb'):
            b['thumb'] = str(b['thumb'])
        banners.append(b)
    return jsonify(banners)

@app.route('/edit_banner/<banner_id>', methods=['POST'])
def edit_banner(banner_id):
    if 'admin' not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    banner = mongo.db.banners.find_one({'_id': ObjectId(banner_id)})
    if not banner:
        return jsonify({"success": False, "error": "Banner not found"}), 404

    title = request.form.get('title', banner.get('title'))
    content = request.form.get('content', banner.get('content'))
    tags = [t.strip() for t in request.form.get('tags', ','.join(banner.get('tags', []))).split(',') if t.strip()]

    # Update image if provided
    file = request.files.get('image')
    if file and file.filename:
        file_id = fs.put(file, filename=file.filename, contentType=file.content_type)
        mongo.db.banners.update_one({'_id': ObjectId(banner_id)},
                                    {'$set': {'title': title, 'content': content, 'tags': tags, 'image': str(file_id)}})
    else:
        mongo.db.banners.update_one({'_id': ObjectId(banner_id)},
                                    {'$set': {'title': title, 'content': content, 'tags': tags}})

    updated_banner = mongo.db.banners.find_one({'_id': ObjectId(banner_id)})
    updated_banner["_id"] = str(updated_banner["_id"])
    if updated_banner.get("image"):
        updated_banner["image"] = str(updated_banner["image"])

    socketio.emit('update_banner', updated_banner, namespace='/')
    return jsonify({"success": True, "banner": updated_banner})

@app.route('/delete_banner/<banner_id>', methods=['POST'])
def delete_banner(banner_id):
    if 'admin' not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    result = mongo.db.banners.delete_one({'_id': ObjectId(banner_id)})
    if result.deleted_count == 0:
        return jsonify({"success": False, "error": "Banner not found"}), 404

    socketio.emit('delete_banner', {'_id': banner_id}, namespace='/')
    return jsonify({"success": True})

# ----------------- POST ACTIONS -----------------
@app.route('/add_post', methods=['POST'])
def add_post():
    if 'admin' not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    files_data = []

    for file in request.files.getlist('files'):
        if file and file.filename:
            file_id = fs.put(file.read(), filename=file.filename, content_type=file.mimetype)
            mime_type = file.mimetype or mimetypes.guess_type(file.filename)[0] or ''
            ftype = 'image' if mime_type.startswith('image/') else 'video' if mime_type.startswith('video/') else 'document'
            files_data.append({"file_id": str(file_id), "filename": file.filename, "type": ftype})

    post_doc = {
        "title": title,
        "content": content,
        "files": files_data,
        "likes": 0,
        "likes_users": [],
        "comments": [],
        "date": datetime.now(timezone.utc)
    }

    inserted = mongo.db.posts.insert_one(post_doc)
    post_doc["_id"] = str(inserted.inserted_id)
    serialized = serialize_post(post_doc)

    # Broadcast addition
    socketio.emit('new_post', serialized)
    return jsonify({"success": True, "post": serialized})

@app.route('/update_post/<post_id>', methods=['POST'])
def update_post(post_id):
    if 'admin' not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        post_obj = mongo.db.posts.find_one({'_id': ObjectId(post_id)})
    except Exception:
        return jsonify({"success": False, "error": "Invalid ID"}), 400

    if not post_obj:
        return jsonify({"success": False, "error": "Post not found"}), 404

    # Get updated fields or fallback to existing
    title = request.form.get('title', post_obj.get('title', '')).strip()
    content = request.form.get('content', post_obj.get('content', '')).strip()
    existing_files = post_obj.get('files', []) or []

    # Append newly uploaded files (if any)
    for file in request.files.getlist('files'):
        if file and file.filename:
            file_id = fs.put(file.read(), filename=file.filename, content_type=file.mimetype)
            mime_type = file.mimetype or mimetypes.guess_type(file.filename)[0] or ''
            ftype = 'image' if mime_type.startswith('image/') else 'video' if mime_type.startswith('video/') else 'document'
            existing_files.append({"file_id": str(file_id), "filename": file.filename, "type": ftype})

    # Update post with new data and timestamp
    mongo.db.posts.update_one(
        {'_id': ObjectId(post_id)},
        {'$set': {'title': title, 'content': content, 'files': existing_files, 'date': datetime.now(timezone.utc)}}
    )

    updated_post = mongo.db.posts.find_one({'_id': ObjectId(post_id)})
    serialized = serialize_post(updated_post)

    # Emit real-time update
    socketio.emit('update_post', serialized, namespace='/')

    return jsonify({"success": True, "post": serialized})

@app.route('/delete_post/<post_id>', methods=['POST'])
def delete_post(post_id):
    if 'admin' not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        result = mongo.db.posts.delete_one({'_id': ObjectId(post_id)})
    except Exception as e:
        print("Delete error:", e)
        return jsonify({"success": False, "error": "Invalid ID"}), 400

    if result.deleted_count == 0:
        return jsonify({"success": False, "error": "Post not found"}), 404

    # notify clients
    socketio.emit('delete_post', {'_id': post_id}, namespace='/')
    return jsonify({"success": True})


# ----------------- GET FILE (GridFS) -----------------
@app.route('/file/<file_id>')
def get_file(file_id):
    try:
        gf = fs.get(ObjectId(file_id))
    except Exception as e:
        print(f"File not found for ID {file_id}: {e}")
        return Response("File not found", status=404)

    mime_type = gf.content_type

    if not mime_type:
        filename = getattr(gf, "filename", "")
        mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

    file_bytes = BytesIO(gf.read())

    if mime_type.startswith(('image/', 'video/')):
        return send_file(file_bytes, mimetype=mime_type)
    else:
        return send_file(
            file_bytes,
            mimetype=mime_type,
            as_attachment=True,
            download_name=getattr(gf, "filename", "file")
        )

# ----------------- USER AUTH -----------------
@app.route('/user_auth', methods=['GET', 'POST'])
def user_auth():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'signup':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')

            # Check if username or email already exists
            if mongo.db.users.find_one({'$or': [{'username': username}, {'email': email}]}):
                flash("Username or Email already exists!")
                return redirect(url_for('user_auth'))

            # Insert new user
            mongo.db.users.insert_one({
                'username': username,
                'email': email,
                'password': password
            })
            session['user'] = username
            flash("Signup successful! You are now logged in.")
            return redirect(url_for('index'))

        elif action == 'signin':
            identifier = request.form.get('username')  # can be username or email
            password = request.form.get('password')

            # Try finding user by username or email
            user = mongo.db.users.find_one({'$or': [{'username': identifier}, {'email': identifier}]})

            if user and user['password'] == password:
                session['user'] = user['username']
                flash("Login successful!")
                return redirect(url_for('index'))
            else:
                flash("Invalid username/email or password")
                return redirect(url_for('user_auth'))

    return render_template('user_auth.html')

@app.route('/update_user', methods=['POST'])
def update_user():
    username = session.get('user')
    if not username:
        return jsonify({'error': 'not_logged_in'}), 401

    user = mongo.db.users.find_one({'username': username})
    if not user:
        return jsonify({'error': 'user_not_found'}), 404
    user_id = user['_id']

    # --- Username Update ---
    if 'username' in request.form:
        new_username = request.form['username'].strip()
        mongo.db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'username': new_username}})
        session['user'] = new_username 
    
    # --- Profile Image Update ---
    if 'profile_pic' in request.files:
        file = request.files['profile_pic']
        filename = secure_filename(file.filename)
        
        # Delete old profile image
        old_user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        if old_user.get('profile_pic'):
            try:
                fs.delete(ObjectId(old_user['profile_pic']))
            except:
                pass

        # Save new image in GridFS
        file_id = fs.put(file, filename=filename, content_type=file.content_type)
        mongo.db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'profile_pic': file_id}})
        
        # Update session to use in template
        session['user_img'] = url_for('get_profile', user_id=user_id)
        
    return jsonify({'message': 'User updated successfully'})

@app.route('/get_profile/<user_id>')
def get_profile(user_id):
    user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if not user or not user.get('profile_pic'):
        return '', 404
    file = fs.get(ObjectId(user['profile_pic']))
    return Response(file.read(), mimetype=file.content_type)

@app.route('/posts_partial')
def posts_partial():
    posts_cursor = mongo.db.posts.find().sort('date', -1)
    posts = [serialize_post(p) for p in posts_cursor]
    return render_template('_posts_partial.html', posts=posts)

# ----------------- INTERACTIONS -----------------
@app.route('/like/<post_id>', methods=['POST'])
def like_post(post_id):
    if 'user' not in session:
        return jsonify({'error': 'login_required'}), 401

    user = session['user']
    post = mongo.db.posts.find_one({'_id': ObjectId(post_id)})
    if not post:
        return jsonify({'error': 'Post not found'}), 404

    likes = post.get('likes_users', [])

    if user in likes:
        likes.remove(user)
    else:
        likes.append(user)

    mongo.db.posts.update_one(
        {'_id': ObjectId(post_id)},
        {'$set': {'likes_users': likes, 'likes': len(likes)}}
    )

    # Emit real-time update to all clients
    socketio.emit('update_likes', {
        'post_id': post_id,
        'likes': len(likes),
        'liked_by_current_user': user in likes
    })

    return jsonify({'likes': len(likes), 'liked': user in likes})



@app.route('/comment/<post_id>', methods=['POST'])
def add_comment(post_id):
    if 'user' not in session:
        return jsonify({"error": "login_required"}), 401

    user_doc = mongo.db.users.find_one({'username': session['user']})
    if not user_doc:
        return jsonify({"error": "user_not_found"}), 404

    text = request.form.get('text', '').strip()
    if not text:
        return jsonify({"error": "empty_comment"}), 400

    comment = {
        'user_id': user_doc.get('_id'),
        'username': user_doc.get('username'),
        'text': text,
        'date': datetime.now(timezone.utc)
    }

    mongo.db.posts.update_one(
        {'_id': ObjectId(post_id)},
        {'$push': {'comments': comment}}
    )

    # Emit real-time comment
    socketio.emit('new_comment', {
        'post_id': post_id,
        'comment': {
            'user_id': _ensure_str(comment['user_id']),
            'username': comment['username'],
            'text': comment['text'],
            'date': comment['date'].isoformat()
        }
    })

    return jsonify(success=True)

# ----------------- SOCKET EVENTS (optional server handlers) -----------------
@socketio.on('connect')
def on_connect():
    # helpful for debugging - clients can see connection
    print("Client connected:", request.sid)


@socketio.on('disconnect')
def on_disconnect():
    print("Client disconnected:", request.sid)


# ----------------- LOGOUT / CACHE -----------------
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('index'))


@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response


# ----------------- RUN APP -----------------
if __name__ == '__main__':
    # Use socketio.run to enable WebSocket handling
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
