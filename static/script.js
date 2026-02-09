const fileInp = document.getElementById('fileInp');
const artist = document.getElementById('artist');
const title = document.getElementById('title');
const album = document.getElementById('album');
const coverBox = document.getElementById('coverBox');
const coverImg = document.getElementById('coverImg');
const form = document.getElementById('mainForm');
const progBar = document.getElementById('progBar');

fileInp.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;

    window.jsmediatags.read(file, {
        onSuccess: function(tag) {
            const t = tag.tags;
            artist.value = t.artist || "";
            title.value = t.title || "";
            album.value = t.album || "";
            
            if (t.picture) {
                const { data, format } = t.picture;
                let base64 = "";
                for (let i = 0; i < data.length; i++) base64 += String.fromCharCode(data[i]);
                coverImg.src = `data:${format};base64,${window.btoa(base64)}`;
                coverBox.style.display = "block";
            } else {
                coverBox.style.display = "none";
            }
        },
        onError: () => coverBox.style.display = "none"
    });
});

form.addEventListener('submit', () => {
    document.getElementById('loading').style.display = 'block';
    document.getElementById('btnGo').style.display = 'none';
    let p = 0;
    const interval = setInterval(() => {
        if (p < 95) {
            p += 1.5;
            progBar.style.width = p + "%";
        } else {
            clearInterval(interval);
        }
    }, 150);
});