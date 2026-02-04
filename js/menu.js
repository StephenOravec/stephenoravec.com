(function() {
    // Menu content
    const menuItems = [
        { label: 'signal', href: '/' },
        { label: 'books', href: '/books' },
        { label: 'profiles', href: '/profiles' }
    ];

    // Find the header
    const header = document.querySelector('.header');
    if (!header) return;

    // Create hamburger button
    const hamburger = document.createElement('button');
    hamburger.className = 'hamburger';
    hamburger.setAttribute('aria-label', 'Toggle menu');
    hamburger.setAttribute('aria-expanded', 'false');
    hamburger.innerHTML = 
        '<span class="hamburger-line"></span>' +
        '<span class="hamburger-line"></span>' +
        '<span class="hamburger-line"></span>';

    // Create nav menu
    const navMenu = document.createElement('nav');
    navMenu.className = 'nav-menu';

    const ul = document.createElement('ul');
    menuItems.forEach(function(item) {
        const li = document.createElement('li');
        const a = document.createElement('a');
        a.href = item.href;
        a.textContent = item.label;
        li.appendChild(a);
        ul.appendChild(li);
    });
    navMenu.appendChild(ul);

    // Add to header
    header.appendChild(hamburger);
    header.appendChild(navMenu);

    // Toggle functionality
    hamburger.addEventListener('click', function() {
        hamburger.classList.toggle('active');
        navMenu.classList.toggle('active');
        const expanded = hamburger.getAttribute('aria-expanded') === 'true';
        hamburger.setAttribute('aria-expanded', !expanded);
    });
})();