// ======================
// ADMIN.JS
// ======================

// Track current post/banner being edited or deleted
let currentPostId = null;
let currentEditBanner = null;
let bannerToDelete = null;

// Initialize Socket.IO
const socket = io(location.origin, { transports: ['websocket', 'polling'] });

// ======================
// DELETE POST
// ======================
function confirmDelete(postId) {
    currentPostId = postId;
    document.getElementById('deleteModal').style.display = 'block';
}

document.getElementById('deleteConfirmBtn').onclick = function () {
    if (currentPostId) {
        fetch(`/delete_post/${currentPostId}`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    document.getElementById(currentPostId)?.remove();
                    document.getElementById('deleteModal').style.display = 'none';
                } else {
                    alert(data.error || "Failed to delete post");
                }
            })
            .catch(console.error);
    } else if (bannerToDelete) {
        deleteBanner(bannerToDelete);
    }
};

function closeDeleteModal() {
    document.getElementById('deleteModal').style.display = 'none';
    currentPostId = null;
    bannerToDelete = null;
}

// ======================
// EDIT POST
// ======================
function openEditModal(postId) {
    fetch(`/get_post/${postId}`)
        .then(res => res.json())
        .then(data => {
            if (data.error) return alert(data.error);

            currentPostId = data._id;
            document.getElementById('editTitle').value = data.title;
            document.getElementById('editContent').value = data.content;
            document.getElementById('editModal').style.display = 'block';
        })
        .catch(console.error);
}

function saveEdit() {
    const formData = new FormData();
    formData.append('title', document.getElementById('editTitle').value);
    formData.append('content', document.getElementById('editContent').value);

    const files = document.getElementById('editFiles').files;
    for (let f of files) formData.append('files', f);

    fetch(`/update_post/${currentPostId}`, { method: 'POST', body: formData })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('editModal').style.display = 'none';
                window.location.reload();
            } else alert(data.error || "Failed to update post");
        })
        .catch(console.error);
}

function closeEditModal() {
    document.getElementById('editModal').style.display = 'none';
}

// ======================
// PUBLISH NEW POST
// ======================
document.getElementById('publishForm')?.addEventListener('submit', (e) => {
    e.preventDefault();

    const formData = new FormData();
    formData.append('title', document.getElementById('title').value.trim());
    formData.append('content', document.getElementById('content').value.trim());

    const files = document.getElementById('postFiles').files;
    for (let f of files) {
        formData.append('files', f);
    }

    fetch('/add_post', { method: 'POST', body: formData })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // Clear the form
                document.getElementById('publishForm').reset();
                // Post will automatically appear via socket, no reload needed
                console.log('Post published:', data.post);
            } else {
                alert(data.error || "Failed to publish post");
            }
        })
        .catch(console.error);
});

// ======================
// REAL-TIME SOCKET EVENTS
// ======================
socket.on('new_post', (post) => {
    if (document.getElementById(post._id)) return; // avoid duplicates

    // Build file HTML if files exist
    let filesHTML = '';
    if (post.files && post.files.length > 0) {
        filesHTML = '<div class="post-files">';
        post.files.forEach(f => {
            if (f.type === 'image') {
                filesHTML += `<img src="/file/${f.file_id}" alt="${f.filename}" style="max-width:200px;"/>`;
            } else if (f.type === 'video') {
                filesHTML += `<video controls style="max-width:200px;"><source src="/file/${f.file_id}" type="video/mp4"></video>`;
            } else {
                filesHTML += `<a href="/file/${f.file_id}" target="_blank">${f.filename}</a>`;
            }
        });
        filesHTML += '</div>';
    }

    const div = document.createElement('div');
    div.className = 'post-card';
    div.id = post._id;

    div.innerHTML = `
        <h3>${post.title}</h3>
        <p>${post.content}</p>
        ${filesHTML}
        <button onclick="openEditModal('${post._id}')">Edit</button>
        <button onclick="confirmDelete('${post._id}')">Delete</button>
    `;
    document.getElementById('posts').prepend(div);
});

// ======================
// ===== BANNER SECTION =====
// ======================

const bannerForm = document.getElementById('bannerForm');
const bannerSlider = document.getElementById('bannerSlider');

// Add Banner
bannerForm?.addEventListener('submit', async e => {
    e.preventDefault();
    const formData = new FormData(bannerForm);

    const res = await fetch('/add_banner', { method: 'POST', body: formData });
    const data = await res.json();

    if (data.success) {
        bannerForm.reset();
        console.log('Banner added:', data.banner);
    } else {
        alert('Failed to add banner');
    }
});

// Real-time banner updates
socket.on('new_banner', banner => {
    const slide = document.createElement('div');
    slide.classList.add('slide');
    slide.id = `banner-${banner._id}`;
    slide.innerHTML = `
        <div class="overlay">
            <h3>${banner.title}</h3>
            <p>${banner.content}</p>
            <p class="tags">${banner.tags.join(', ')}</p>
            <button onclick="editBanner('${banner._id}')">Edit</button>
            <button onclick="deleteBanner('${banner._id}')">Delete</button>
        </div>
    `;
    bannerSlider.prepend(slide);
    renderBanner(banner);
});


// Edit/Delete Functions
let currentEditId = null;
function editBanner(id) {
    currentEditId = id;
    const slide = document.getElementById(`banner-${id}`);
    document.getElementById('editBannerTitle').value = slide.querySelector('h3').innerText;
    document.getElementById('editBannerContent').value = slide.querySelector('p').innerText;
    document.getElementById('editBannerTags').value = slide.querySelector('.tags').innerText;
    document.getElementById('editBannerModal').style.display = 'block';
}

function closeEditBannerModal() {
    document.getElementById('editBannerModal').style.display = 'none';
    currentEditId = null;
}

document.getElementById('editBannerForm')?.addEventListener('submit', async e => {
    e.preventDefault();
    if (!currentEditId) return;
    const formData = new FormData(e.target);
    const res = await fetch(`/edit_banner/${currentEditId}`, { method: 'POST', body: formData });
    const data = await res.json();
    if (data.success) closeEditBannerModal();
});

async function deleteBanner(id) {
    if (!confirm('Delete this banner?')) return;
    const res = await fetch(`/delete_banner/${id}`, { method: 'POST' });
    const data = await res.json();
    if (data.success) document.getElementById(`banner-${id}`)?.remove();
}

// Drag-scroll for slider
let isDown = false, startX, scrollLeft;
bannerSlider?.addEventListener('mousedown', e => {
    isDown = true;
    bannerSlider.classList.add('active');
    startX = e.pageX - bannerSlider.offsetLeft;
    scrollLeft = bannerSlider.scrollLeft;
});
bannerSlider?.addEventListener('mouseleave', () => { isDown = false; bannerSlider.classList.remove('active'); });
bannerSlider?.addEventListener('mouseup', () => { isDown = false; bannerSlider.classList.remove('active'); });
bannerSlider?.addEventListener('mousemove', e => {
    if (!isDown) return;
    e.preventDefault();
    const x = e.pageX - bannerSlider.offsetLeft;
    bannerSlider.scrollLeft = scrollLeft - (x - startX) * 2;
});

// Render a banner in the slider (reuse for existing + new banners)
function renderBanner(banner) {
    if (document.getElementById(`banner-${banner._id}`)) return; // avoid duplicates

    const slide = document.createElement('div');
    slide.classList.add('slide');
    slide.id = `banner-${banner._id}`;
    slide.innerHTML = `
        <div class="overlay">
            <h3>${banner.title}</h3>
            <p>${banner.content}</p>
            <p class="tags">${(banner.tags || []).join(', ')}</p>
            <button onclick="editBanner('${banner._id}')">Edit</button>
            <button onclick="deleteBanner('${banner._id}')">Delete</button>
        </div>
    `;
    bannerSlider.prepend(slide);
}

// Load existing banners from server
async function loadBanners() {
    try {
        const res = await fetch('/get_banners');
        const banners = await res.json();
        banners.forEach(b => renderBanner(b));
    } catch (err) {
        console.error("Failed to load banners:", err);
    }
}

// Call this on page load
loadBanners();

const slider = document.querySelector('.slider');

slider.addEventListener('wheel', (e) => {
    e.preventDefault();
    const speed = 2.5; // increase this number for faster scroll
    slider.scrollLeft += e.deltaY * speed;
});


