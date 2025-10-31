// ===== Profile Dropdown & Edit =====
const profile = document.getElementById('profile');
const dropdown = document.getElementById('profileDropdown');
const editBtn = document.getElementById('editBtn');
const editSection = document.getElementById('editSection');
const detailName = document.getElementById('detailName');
const detailImg = document.getElementById('detailImg');
const profileImg = document.getElementById('profileImg');
const usernameSpan = document.getElementById('username');
const editUsername = document.getElementById('editUsername');
const saveUsername = document.getElementById('saveUsername');
const editProfileImg = document.getElementById('editProfileImg');
const logoutBtn = document.getElementById('logoutBtn');

// Toggle dropdown
profile.addEventListener('click', e => {
    dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
});
dropdown.addEventListener('click', e => e.stopPropagation());
document.addEventListener('click', e => {
    if (!profile.contains(e.target)) dropdown.style.display = 'none';
});

// Toggle edit section
editBtn.addEventListener('click', () => {
    editSection.style.display = editSection.style.display === 'block' ? 'none' : 'block';
});

async function updateUser({ username, file }) {
    const formData = new FormData();
    if (username) formData.append('username', username);
    if (file) formData.append('profile_pic', file);

    try {
        const res = await fetch('/update_user', {
            method: 'POST',
            body: formData,
            credentials: 'same-origin'
        });
        const data = await res.json();
        if (data.message) {
            alert(data.message);

            // Reload profile image
            const profileImg = document.getElementById('profileImg');
            const detailImg = document.getElementById('detailImg');

            // Add timestamp to prevent caching
            const timestamp = new Date().getTime();

            if (profileImg) profileImg.src = `/get_profile/${data.user_id}?t=${timestamp}`;
            if (detailImg) detailImg.src = `/get_profile/${data.user_id}?t=${timestamp}`;

            return data.message;
        } else throw new Error('Update failed');
    } catch (err) {
        console.error(err);
        alert('Update failed!');
    }
}

// Save username
saveUsername.addEventListener('click', async () => {
    const newName = editUsername.value.trim();
    if (!newName) return;

    const message = await updateUser({ username: newName });
    if (message) {
        usernameSpan.textContent = newName;
        detailName.textContent = newName;
        editUsername.value = '';
        editSection.style.display = 'none';
        alert(message);
    }
});

// Change profile image
editProfileImg.addEventListener('change', async e => {
    const file = e.target.files[0];
    if (!file) return;

    // Preview image
    const reader = new FileReader();
    reader.onload = function (ev) {
        profileImg.src = ev.target.result;
        detailImg.src = ev.target.result;
    };
    reader.readAsDataURL(file);

    const message = await updateUser({ file });
    if (message) alert(message);
});

// Logout
logoutBtn.addEventListener('click', () => {
    window.location.href = '/logout';
});
