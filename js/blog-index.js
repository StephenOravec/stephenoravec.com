(function() {
    const feedContainer = document.getElementById('blog-feed');
    const loadMoreButton = document.getElementById('load-more-button');
    const version = window.BLOG_VERSION || '';

    let manifest = null;
    let nextChunk = 1;

    function buildCard(post) {
        const article = document.createElement('article');
        article.className = 'blog-card';
        article.dataset.slug = post.slug;
        article.dataset.type = post.type;

        const titleLink = document.createElement('a');
        titleLink.href = post.url;
        titleLink.className = 'blog-card-title-link';
        const title = document.createElement('h2');
        title.className = 'blog-card-title';
        title.textContent = post.title;
        titleLink.appendChild(title);

        const time = document.createElement('time');
        time.className = 'blog-card-date';
        time.dateTime = post.date;
        time.textContent = post.display_date;

        const imageLink = document.createElement('a');
        imageLink.href = post.url;
        imageLink.className = 'blog-card-image-link';
        const img = document.createElement('img');
        img.className = 'blog-card-image';
        img.src = post.image_url;
        img.srcset = `${post.image_url_400} 400w, ${post.image_url_1000} 1000w, ${post.image_url_2000} 2000w`;
        img.sizes = '(max-width: 768px) 100vw, 1000px';
        img.alt = post.image_alt;
        img.loading = 'lazy';
        imageLink.appendChild(img);

        const description = document.createElement('p');
        description.className = 'blog-card-description';
        description.innerHTML = post.description_html;

        article.appendChild(titleLink);
        article.appendChild(time);
        article.appendChild(imageLink);
        article.appendChild(description);

        if (post.has_body && post.body_html) {
            const expandButton = document.createElement('button');
            expandButton.className = 'blog-card-expand-button';
            expandButton.textContent = 'Read more';
            expandButton.setAttribute('aria-expanded', 'false');

            const bodyContainer = document.createElement('div');
            bodyContainer.className = 'blog-card-body';
            bodyContainer.innerHTML = post.body_html;
            bodyContainer.hidden = true;

            expandButton.addEventListener('click', function() {
                const isExpanded = expandButton.getAttribute('aria-expanded') === 'true';
                if (isExpanded) {
                    bodyContainer.hidden = true;
                    expandButton.setAttribute('aria-expanded', 'false');
                    expandButton.textContent = 'Read more';
                } else {
                    bodyContainer.hidden = false;
                    expandButton.setAttribute('aria-expanded', 'true');
                    expandButton.textContent = 'Collapse';
                }
            });

            article.appendChild(expandButton);
            article.appendChild(bodyContainer);
        }

        return article;
    }

    function renderChunk(chunkData) {
        chunkData.posts.forEach(post => {
            const card = buildCard(post);
            feedContainer.appendChild(card);
        });
    }

    function updateLoadMoreButton() {
        if (nextChunk <= manifest.chunk_count) {
            loadMoreButton.hidden = false;
        } else {
            loadMoreButton.hidden = true;
        }
    }

    function fetchChunk(number) {
        return fetch(`/blog/data/posts-${number}.json?v=${version}`)
            .then(response => response.json());
    }

    function loadNextChunk() {
        if (nextChunk > manifest.chunk_count) {
            return;
        }
        loadMoreButton.disabled = true;
        fetchChunk(nextChunk).then(chunkData => {
            renderChunk(chunkData);
            nextChunk += 1;
            loadMoreButton.disabled = false;
            updateLoadMoreButton();
        }).catch(err => {
            console.error('Failed to load chunk', err);
            loadMoreButton.disabled = false;
        });
    }

    function init() {
        fetch(`/blog/data/manifest.json?v=${version}`)
            .then(response => response.json())
            .then(data => {
                manifest = data;
                loadNextChunk();
            })
            .catch(err => {
                console.error('Failed to load manifest', err);
                feedContainer.textContent = 'Unable to load posts.';
            });
    }

    loadMoreButton.addEventListener('click', loadNextChunk);
    init();
})();