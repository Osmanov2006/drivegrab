"""JavaScript snippets that run inside the Drive pages."""

# Every loaded page of the Drive viewer is an <img> with a blob: src.
# For each one we return its index and its y position inside the scroll
# container - Drive unloads pages that scroll far off screen, so the
# position is what lets us put pages back in order later.
SCAN_PAGES = """() => {
    const res = [];
    let atBottom = false;
    const imgs = [...document.images];
    for (let i = 0; i < imgs.length; i++) {
        const img = imgs[i];
        if (!img.src.startsWith('blob:https://drive.google.com/')) continue;
        if (!img.complete || !img.naturalWidth) continue;

        let box = img.parentElement;
        while (box && box.scrollHeight <= box.clientHeight + 5) box = box.parentElement;
        const boxTop = box ? box.getBoundingClientRect().top : 0;
        const st = box ? box.scrollTop : window.scrollY;
        if (box) atBottom = box.scrollTop + box.clientHeight >= box.scrollHeight - 5;

        res.push({
            i: i,
            y: Math.round(img.getBoundingClientRect().top - boxTop + st),
            w: img.naturalWidth
        });
    }
    return { pages: res, atBottom: atBottom };
}"""

# Draw one page onto a canvas and export it as JPEG.
# White fill first, otherwise transparent areas turn black in JPEG.
GRAB_PAGE = """([i, quality]) => {
    const img = document.images[i];
    const c = document.createElement('canvas');
    c.width = img.naturalWidth;
    c.height = img.naturalHeight;
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, c.width, c.height);
    ctx.drawImage(img, 0, 0);
    return c.toDataURL('image/jpeg', quality);
}"""

# embeddedfolderview is a plain HTML listing Google serves for embedding
# folders - much easier to parse than the main Drive UI.
LIST_FOLDER = """() => [...document.querySelectorAll('.flip-entry')].map(e => {
    const a = e.querySelector('a');
    const t = e.querySelector('.flip-entry-title');
    return {
        href: a ? a.href : '',
        id: (e.id || '').replace('entry-', ''),
        name: t ? t.textContent.trim() : ''
    };
})"""

FILE_TITLE = """() =>
    document.querySelector('meta[itemprop="name"]')?.content || document.title"""
