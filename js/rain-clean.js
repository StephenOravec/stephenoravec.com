// Cablepunk Clean Signal
(function() {
    const canvas = document.getElementById('rain-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    // Character set
    const chars = [
        //  こんにちは。私の名前はケーブルパンクです。
        'こ', 'ん', 'に', 'ち', 'は', '。', '私', 'の', '名', '前',
        'は', 'ケ', 'ー', 'ブ', 'ル', 'パ', 'ン', 'ク', 'で', 'す',
        // Box drawing / technical
        '│', '┃', '║', '┊', '┆', '╎', '╏',
        '─', '━', '═', '┄', '┈',
        '┌', '┐', '└', '┘', '├', '┤', '┬', '┴', '┼',
        '╔', '╗', '╚', '╝', '╠', '╣', '╦', '╩', '╬',
        // Arrows
        '↑', '↑', '↓', '↓', '←', '→', '←', '→', '↔', '↕', '⇅', '⇄',
        // Binary
        '0', 'b', '1', '1', '1', '1', '0', '1', '1', '1', '0', '1', '0',
        // Electrical
        '⏚', '⎓', '⌁', '⚡', '◈', '◇', '○', '●',
        // Latin
        'S', 'T', 'E', 'P', 'H', 'E', 'N', 'O', 'R', 'A', 'V', 'E', 'C',
        'C', 'A', 'B', 'L', 'E', 'P', 'U', 'N', 'K', 'P', 'R', 'E', 'S', 'S'
    ];

    const layers = [
        { fontSize: 18, opacity: 0.4, speedMin: 0.15, speedMax: 0.25, trailLength: 12 },
        { fontSize: 24, opacity: 0.7, speedMin: 0.2, speedMax: 0.35, trailLength: 10 },
        { fontSize: 32, opacity: 1.0, speedMin: 0.25, speedMax: 0.45, trailLength: 8 }
    ];

    function getRedColor(brightness, opacity) {
        const r = Math.floor(140 + brightness * 115);
        const g = Math.floor(brightness * 45);
        const b = Math.floor(30 + brightness * 40);
        return 'rgba(' + r + ',' + g + ',' + b + ',' + (opacity * brightness) + ')';
    }

    function getSilverColor(brightness, opacity) {
        const base = Math.floor(160 + brightness * 95);
        return 'rgba(' + base + ',' + base + ',' + Math.floor(base * 0.95) + ',' + (opacity * brightness) + ')';
    }

    function createStream(x, layer) {
        const stream = {
            x: x,
            layer: layer,
            fontSize: layer.fontSize,
            speed: layer.speedMin + Math.random() * (layer.speedMax - layer.speedMin),
            isSilver: Math.random() < 0.15,
            trailLength: layer.trailLength,
            opacity: layer.opacity,
            trail: [],
            headY: Math.random() * -canvas.height,
            charQueue: [],
            charIndex: 0
        };

        function refreshChars() {
            stream.charQueue = [];
            for (let i = 0; i < 50; i++) {
                stream.charQueue.push(chars[Math.floor(Math.random() * chars.length)]);
            }
            stream.charIndex = 0;
        }
        refreshChars();

        stream.nextChar = function() {
            const char = stream.charQueue[stream.charIndex];
            stream.charIndex = (stream.charIndex + 1) % stream.charQueue.length;
            if (stream.charIndex === 0) refreshChars();
            return char;
        };

        stream.update = function() {
            stream.headY += stream.speed * stream.fontSize;

            if (stream.trail.length === 0 || stream.headY - stream.trail[0].y >= stream.fontSize) {
                stream.trail.unshift({
                    char: stream.nextChar(),
                    y: stream.headY,
                    age: 0
                });
            }

            for (let i = 0; i < stream.trail.length; i++) {
                stream.trail[i].age++;
            }

            const maxAge = stream.trailLength * 3;
            stream.trail = stream.trail.filter(function(t) {
                return t.age < maxAge;
            });

            if (stream.trail.length > 0) {
                const lastY = stream.trail[stream.trail.length - 1].y;
                if (lastY > canvas.height + stream.fontSize * stream.trailLength) {
                    stream.headY = Math.random() * -200 - 50;
                    stream.trail = [];
                    stream.speed = stream.layer.speedMin + Math.random() * (stream.layer.speedMax - stream.layer.speedMin);
                    stream.isSilver = Math.random() < 0.15;
                }
            }
        };

        stream.draw = function(ctx) {
            ctx.font = stream.fontSize + 'px monospace';

            for (let i = 0; i < stream.trail.length; i++) {
                const t = stream.trail[i];
                if (t.y < 0 || t.y > canvas.height + stream.fontSize) continue;

                const brightness = Math.max(0, 1 - (i / stream.trailLength));

                if (brightness > 0) {
                    if (stream.isSilver) {
                        ctx.fillStyle = getSilverColor(brightness, stream.opacity);
                    } else {
                        ctx.fillStyle = getRedColor(brightness, stream.opacity);
                    }
                    ctx.fillText(t.char, stream.x, t.y);
                }
            }
        };

        return stream;
    }

    let streams = [];
    let animationId;

    function initStreams() {
        streams = [];

        const baseColumnWidth = 16;
        const numColumns = Math.ceil(canvas.width / baseColumnWidth);

        for (let i = 0; i < numColumns; i++) {
            const x = i * baseColumnWidth;

            layers.forEach(function(layer) {
                let spawnChance;
                if (layer.fontSize === 18) {
                    spawnChance = 0.7;
                } else if (layer.fontSize === 24) {
                    spawnChance = 0.4;
                } else {
                    spawnChance = 0.25;
                }

                if (Math.random() < spawnChance) {
                    streams.push(createStream(x, layer));
                }
            });
        }

        streams.sort(function(a, b) {
            return a.fontSize - b.fontSize;
        });
    }

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        initStreams();
    }

    resize();
    window.addEventListener('resize', resize);

    let lastTime = 0;
    const targetFPS = 45;
    const frameInterval = 1000 / targetFPS;

    function draw(currentTime) {
        animationId = requestAnimationFrame(draw);

        const deltaTime = currentTime - lastTime;
        if (deltaTime < frameInterval) return;
        lastTime = currentTime - (deltaTime % frameInterval);

        ctx.fillStyle = '#0a0a0f';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        for (let i = 0; i < streams.length; i++) {
            streams[i].update();
            streams[i].draw(ctx);
        }
    }

    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            cancelAnimationFrame(animationId);
        } else {
            lastTime = 0;
            animationId = requestAnimationFrame(draw);
        }
    });

    animationId = requestAnimationFrame(draw);
})();