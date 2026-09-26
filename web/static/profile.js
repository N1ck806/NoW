/* ============================================
   NIGHTMARE • PROFILE EFFECTS (v4)
   Хоррор-эффекты + роли.
   - Tier-эффекты (статус в Discord)
   - Coder-режим: глитчи, матрица, курсор (БЕЗ терминала снизу)
   - Admin-режим: золотые искры
   - Ghost-режим: мерцание
   ============================================ */

(function () {
    'use strict';

    // ============================================
    // 0. УТИЛИТЫ
    // ============================================

    const rand = (min, max) => Math.random() * (max - min) + min;
    const randInt = (min, max) => Math.floor(rand(min, max + 1));
    const pick = arr => arr[randInt(0, arr.length - 1)];

    // ============================================
    // 1. КОНТЕКСТ СТРАНИЦЫ
    // ============================================

    const page = document.querySelector('.profile-page');
    if (!page) return;

    const tier = parseInt(page.dataset.tier || '0', 10);
    const userId = page.dataset.userId || '';
    const isAdmin = page.dataset.isAdmin === '1';
    const isCoder = page.dataset.isCoder === '1';

    // ============================================
    // 2. ПУТИ К SVG
    // ============================================

    const SVG = {
        bloodDrop: '/static/img/svg/blood-drop.svg',
        smoke:     '/static/img/svg/smoke.svg',
        crack:     '/static/img/svg/crack.svg',
        eye:       '/static/img/svg/eye.svg',
        claw:      '/static/img/svg/claw.svg',
        ghost:     '/static/img/svg/ghost.svg',
        spider:    '/static/img/svg/spider.svg',
        web:       '/static/img/svg/web.svg',
        ritual:    '/static/img/svg/ritual.svg',
        skull:     '/static/img/svg/skull.svg',
        noise:     '/static/img/svg/noise.svg',
        bat:       '/static/img/svg/bat.svg',
        chain:     '/static/img/svg/chain.svg',
        hand:      '/static/img/svg/hand.svg',
        portal:    '/static/img/svg/portal.svg',
    };

    // ============================================
    // 3. КОНТЕЙНЕР ДЛЯ ЭФФЕКТОВ
    // ============================================

    let fxLayer = document.getElementById('horrorLayer');
    if (!fxLayer) {
        fxLayer = document.createElement('div');
        fxLayer.id = 'horrorLayer';
        fxLayer.className = 'horror-layer';
        document.body.appendChild(fxLayer);
    }

    // ============================================
    // 4. СОЗДАНИЕ SVG-ЭЛЕМЕНТА
    // ============================================

    function spawnSVG(src, opts = {}) {
        const img = document.createElement('img');
        img.src = src;
        img.className = 'svg-effect ' + (opts.className || 'svg-effect--pop');
        img.alt = '';
        img.draggable = false;

        // ИСПРАВЛЕНО: не ловит клики
        img.style.pointerEvents = 'none';
        img.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
        });

        const size = opts.size || randInt(80, 160);

        img.style.width = size + 'px';
        img.style.height = 'auto';

        if (opts.x !== undefined) img.style.left = opts.x + 'px';
        if (opts.y !== undefined) img.style.top = opts.y + 'px';

        if (opts.duration) {
            img.style.animationDuration = opts.duration + 's';
        }

        fxLayer.appendChild(img);

        const ttl = (opts.duration || 3) * 1000 + 500;
        setTimeout(() => img.remove(), ttl);

        return img;
    }

    // ============================================
    // 5. КЛИК ПО АВАТАРКЕ
    // ============================================

    const avatar = document.getElementById('profileAvatar');
    if (avatar) {
        avatar.addEventListener('click', (e) => {
            e.preventDefault();
            const x = e.clientX;
            const y = e.clientY;

            const effects = ['claw', 'crack', 'bloodDrop', 'eye'];
            const count = Math.min(3 + tier, 10);

            for (let i = 0; i < count; i++) {
                const key = pick(effects);
                setTimeout(() => {
                    spawnSVG(SVG[key], {
                        x: x + rand(-120, 120),
                        y: y + rand(-100, 100),
                        size: randInt(60, 140),
                        className: 'svg-effect--pop',
                        duration: rand(1.8, 2.8),
                    });
                }, i * 80);
            }

            if (tier >= 4) {
                setTimeout(() => spawnScreenGlitch(400), 150);
                setTimeout(() => spawnBloodRain(4), 250);
                setTimeout(() => {
                    spawnSVG(SVG.skull, {
                        x: x + rand(-60, 60),
                        y: y + rand(-40, 40),
                        size: randInt(140, 200),
                        className: 'svg-effect--pop',
                        duration: 2.5,
                    });
                }, 400);
            }

            avatar.style.animation = 'none';
            void avatar.offsetWidth;
            avatar.style.animation = 'avatarShake 0.35s ease-out';
            setTimeout(() => { avatar.style.animation = ''; }, 400);
        });
    }

    // ============================================
    // 6. КНОПКА «ПРИЗВАТЬ ТЬМУ»
    // ============================================

    const btnSummon = document.getElementById('btnSummon');
    if (btnSummon) {
        btnSummon.addEventListener('click', () => summonDarkness());
    }

    function summonDarkness() {
        const summons = ['ghost', 'skull', 'hand', 'bat'];
        const count = 4 + tier;

        for (let i = 0; i < count; i++) {
            setTimeout(() => {
                spawnSVG(pick(summons), {
                    x: rand(0, window.innerWidth - 200),
                    y: rand(window.innerHeight * 0.4, window.innerHeight - 200),
                    size: randInt(120, 240),
                    className: 'svg-effect--rise',
                    duration: rand(3, 4.5),
                });
            }, i * 150);
        }

        for (let i = 0; i < 3; i++) {
            setTimeout(() => {
                spawnSVG(SVG.chain, {
                    x: rand(0, window.innerWidth - 200),
                    y: -100,
                    size: randInt(200, 300),
                    className: 'svg-effect--fall',
                    duration: rand(3, 5),
                });
            }, i * 300);
        }

        spawnBloodRain(Math.min(4 + tier, 15));
        setTimeout(() => spawnScreenGlitch(600), 200);

        document.body.style.animation = 'screenGlitch 0.4s steps(2) 2';
        setTimeout(() => { document.body.style.animation = ''; }, 900);
    }

    // ============================================
    // 7. КНОПКА «ГЛИТЧ»
    // ============================================

    const btnGlitch = document.getElementById('btnGlitch');
    if (btnGlitch) {
        btnGlitch.addEventListener('click', () => triggerGlitch());
    }

    function triggerGlitch() {
        document.body.classList.add('glitching');

        spawnSVG(SVG.noise, {
            x: rand(50, window.innerWidth / 2),
            y: rand(50, window.innerHeight / 2),
            size: randInt(400, 600),
            className: 'svg-effect--pop',
            duration: 1.5,
        });

        for (let i = 0; i < 3; i++) {
            setTimeout(() => {
                spawnSVG(SVG.crack, {
                    x: rand(0, window.innerWidth - 200),
                    y: rand(0, window.innerHeight - 200),
                    size: randInt(150, 300),
                    className: 'svg-effect--pop',
                    duration: 2,
                });
            }, i * 200);
        }

        const glitchBars = 4 + tier;
        for (let i = 0; i < glitchBars; i++) {
            setTimeout(() => spawnGlitchBar(), i * 80);
        }

        setTimeout(() => {
            document.body.classList.remove('glitching');
        }, 900);
    }

    function spawnGlitchBar() {
        const el = document.createElement('div');
        el.style.position = 'fixed';
        el.style.left = '0';
        el.style.right = '0';
        el.style.height = randInt(2, 8) + 'px';
        el.style.top = rand(0, 100) + 'vh';
        el.style.background = Math.random() > 0.5
            ? 'linear-gradient(90deg, transparent, #ff0033, transparent)'
            : 'linear-gradient(90deg, transparent, #00e5ff, transparent)';
        el.style.opacity = '0.8';
        el.style.zIndex = '99999';
        el.style.pointerEvents = 'none';
        el.style.mixBlendMode = 'screen';
        document.body.appendChild(el);

        setTimeout(() => el.remove(), 250);
    }

    function spawnScreenGlitch(duration) {
        document.body.classList.add('glitching');
        setTimeout(() => {
            document.body.classList.remove('glitching');
        }, duration);
    }

    // ============================================
    // 8. КАПЛИ КРОВИ
    // ============================================

    function spawnBloodRain(count) {
        for (let i = 0; i < count; i++) {
            setTimeout(() => {
                spawnSVG(SVG.bloodDrop, {
                    x: rand(0, window.innerWidth - 60),
                    y: -80,
                    size: randInt(24, 56),
                    className: 'svg-effect--fall',
                    duration: rand(2.5, 4.5),
                });
            }, i * 120);
        }
    }

    // ============================================
    // 9. ФОНОВЫЕ SVG ПО ТИРУ
    // ============================================

    if (tier >= 2) {
        const webCorner = document.createElement('img');
        webCorner.src = SVG.web;
        webCorner.className = 'fx-web';
        webCorner.style.top = '0';
        webCorner.style.left = '0';
        webCorner.style.width = '300px';
        webCorner.style.height = 'auto';
        webCorner.style.transformOrigin = 'top left';
        webCorner.style.pointerEvents = 'none';
        document.body.appendChild(webCorner);
    }

    if (tier >= 3) {
        const smoke = document.createElement('img');
        smoke.src = SVG.smoke;
        smoke.className = 'fx-smoke';
        smoke.style.bottom = '-100px';
        smoke.style.left = '-100px';
        smoke.style.width = '600px';
        smoke.style.height = 'auto';
        smoke.style.pointerEvents = 'none';
        document.body.appendChild(smoke);
    }

    if (tier >= 4) {
        const avatarWrap = document.querySelector('.profile-avatar-wrap');
        if (avatarWrap) {
            const ritual = document.createElement('img');
            ritual.src = SVG.ritual;
            ritual.className = 'avatar-backdrop';
            ritual.style.pointerEvents = 'none';
            ritual.style.zIndex = '0';
            avatarWrap.appendChild(ritual);
        }
    }

    if (tier >= 4) {
        setInterval(() => {
            if (Math.random() < 0.4) {
                spawnSVG(SVG.spider, {
                    x: rand(50, window.innerWidth - 150),
                    y: -200,
                    size: randInt(120, 200),
                    className: 'svg-effect--fall',
                    duration: rand(6, 10),
                });
            }
        }, 12000);
    }

    if (tier >= 5) {
        const portal = document.createElement('img');
        portal.src = SVG.portal;
        portal.className = 'fx-portal';
        portal.style.bottom = '20px';
        portal.style.right = '20px';
        portal.style.width = '400px';
        portal.style.height = 'auto';
        portal.style.pointerEvents = 'none';
        document.body.appendChild(portal);

        setInterval(() => {
            if (Math.random() < 0.5) {
                spawnSVG(SVG.bat, {
                    x: -300,
                    y: rand(100, window.innerHeight - 300),
                    size: randInt(300, 450),
                    className: 'svg-effect--fly',
                    duration: rand(6, 9),
                });
            }
        }, 9000);
    }

    // ============================================
    // 10. АВТОМАТИЧЕСКИЕ ЭФФЕКТЫ ПО ТИРУ
    // ============================================

    if (tier >= 4) {
        setInterval(() => {
            if (Math.random() < 0.6) {
                spawnBloodRain(randInt(1, 3));
            }
        }, 5000);
    }

    if (tier >= 4) {
        setInterval(() => {
            if (Math.random() < 0.3) {
                spawnSVG(SVG.eye, {
                    x: rand(0, window.innerWidth - 150),
                    y: rand(0, window.innerHeight - 100),
                    size: randInt(100, 180),
                    className: 'svg-effect--pop',
                    duration: 2.5,
                });
            }
        }, 15000);
    }

    if (tier >= 5) {
        setInterval(() => {
            if (Math.random() < 0.25) {
                spawnScreenGlitch(300);
                spawnGlitchBar();
            }
        }, 8000);

        const WHISPERS = [
            '...он смотрит...',
            '...ты слышишь?...',
            '...за твоей спиной...',
            '...не оборачивайся...',
            '...мы уже здесь...',
            '...ты не один...',
        ];
        setInterval(() => {
            if (Math.random() < 0.2) {
                console.log(
                    '%c' + pick(WHISPERS),
                    'color: #ff0033; font-style: italic; font-size: 14px;'
                );
            }
        }, 15000);
    }

    if (tier >= 2) {
        document.querySelectorAll('.stat-card, .card').forEach(el => {
            el.addEventListener('mouseenter', () => {
                el.style.boxShadow = '0 0 30px rgba(255, 0, 51, 0.3)';
            });
            el.addEventListener('mouseleave', () => {
                el.style.boxShadow = '';
            });
        });
    }

    // ============================================
    // 11. ЭФФЕКТ ПРИ ЗАГРУЗКЕ
    // ============================================

    window.addEventListener('load', () => {
        if (tier >= 3) {
            setTimeout(() => spawnScreenGlitch(300), 400);
        }

        if (tier >= 4) {
            setTimeout(() => spawnBloodRain(3), 800);
        }

        if (tier >= 3) {
            setTimeout(() => {
                spawnSVG(SVG.ghost, {
                    x: rand(0, window.innerWidth - 300),
                    y: rand(0, window.innerHeight * 0.5),
                    size: randInt(200, 350),
                    className: 'svg-effect--rise',
                    duration: rand(4, 6),
                });
            }, 1200);
        }

        const greetings = {
            0: 'Ты зашёл в тень. 👻',
            1: 'Новобранец клана... 🌱',
            2: 'С возвращением, воин. ⚔️',
            3: 'Осторожнее, это владения админа. 🛡️',
            4: 'Здесь правит тьма. 💀',
            5: 'ТЫ. НЕ. ДОЛЖЕН. БЫЛ. ЭТО. ВИДЕТЬ. 👑',
        };
        console.log(
            '%c' + (greetings[tier] || greetings[0]),
            'color: #ff0033; font-family: Impact, sans-serif; font-size: 20px; text-shadow: 0 0 10px #ff0033;'
        );
    });

    // ============================================
    // 12. ДИНАМИЧЕСКИЙ KEYFRAME ДЛЯ АВАТАРКИ
    // ============================================

    const styleEl = document.createElement('style');
    styleEl.textContent = `
        @keyframes avatarShake {
            0%, 100% { transform: translate(0, 0) scale(1.06); }
            20% { transform: translate(-4px, 2px) scale(1.06); }
            40% { transform: translate(4px, -2px) scale(1.06); }
            60% { transform: translate(-3px, -2px) scale(1.06); }
            80% { transform: translate(3px, 2px) scale(1.06); }
        }
    `;
    document.head.appendChild(styleEl);

    // ============================================
    // 13. СЛУЧАЙНЫЕ «ГЛАЗА» В ТЕНИ (tier 5)
    // ============================================

    if (tier >= 5) {
        setInterval(() => {
            if (Math.random() < 0.15) {
                spawnEyes();
            }
        }, 12000);
    }

    function spawnEyes() {
        const el = document.createElement('div');
        el.textContent = '👁️👁️';
        el.style.position = 'fixed';
        el.style.left = rand(0, window.innerWidth - 100) + 'px';
        el.style.top = rand(0, window.innerHeight - 100) + 'px';
        el.style.fontSize = '32px';
        el.style.opacity = '0';
        el.style.zIndex = '99995';
        el.style.pointerEvents = 'none';
        el.style.filter = 'drop-shadow(0 0 15px #ff0033)';
        el.style.transition = 'opacity 0.6s';
        document.body.appendChild(el);

        requestAnimationFrame(() => { el.style.opacity = '0.9'; });

        setTimeout(() => {
            el.style.opacity = '0';
            setTimeout(() => el.remove(), 700);
        }, 2500);
    }

    // ============================================
    // 14. РОЛЬ: CODER
    // Глитчи, матрица, курсор.
    // ТЕРМИНАЛ СНИЗУ УБРАН — будет в личном кабинете.
    // ============================================

    if (isCoder) {
        document.body.classList.add('coder-mode');

        // === 14.1. ПОСТОЯННЫЕ ГОРИЗОНТАЛЬНЫЕ ГЛИТЧ-ПОЛОСЫ ===
        setInterval(() => {
            if (Math.random() < 0.7) {
                spawnGlitchBar();
            }
        }, 1500);

        // === 14.2. СЛУЧАЙНЫЕ СДВИГИ БЛОКОВ ===
        setInterval(() => {
            if (Math.random() < 0.3) {
                const blocks = document.querySelectorAll('.card, .stat-card, .profile-header');
                if (!blocks.length) return;
                const block = pick(Array.from(blocks));
                const shift = rand(-4, 4);
                block.style.transform = `translateX(${shift}px)`;
                block.style.transition = 'transform 0.05s';
                setTimeout(() => {
                    block.style.transform = '';
                    block.style.transition = '';
                }, 100);
            }
        }, 4000);

        // === 14.3. ПАДАЮЩИЙ БИНАРНЫЙ КОД (матрица) ===
        const matrixLayer = document.createElement('div');
        matrixLayer.className = 'coder-matrix';
        matrixLayer.style.pointerEvents = 'none';
        document.body.appendChild(matrixLayer);

        const CHARS = '01アイウエオカキクケコサシスセソタチツテト';
        const COLUMNS = Math.floor(window.innerWidth / 20);

        for (let i = 0; i < COLUMNS; i++) {
            const col = document.createElement('div');
            col.className = 'coder-matrix-col';
            col.style.left = (i * 20) + 'px';
            col.style.animationDelay = rand(0, 5) + 's';
            col.style.animationDuration = rand(6, 12) + 's';

            let chars = '';
            for (let j = 0; j < 15; j++) {
                chars += pick(CHARS.split('')) + '\n';
            }
            col.textContent = chars;
            matrixLayer.appendChild(col);
        }

        // === 14.4. КУРСОР-ТЕРМИНАЛ (следит за мышью) ===
        const customCursor = document.createElement('div');
        customCursor.className = 'coder-cursor';
        customCursor.textContent = '_';
        customCursor.style.pointerEvents = 'none';
        document.body.appendChild(customCursor);

        document.addEventListener('mousemove', (e) => {
            customCursor.style.left = (e.clientX + 15) + 'px';
            customCursor.style.top = (e.clientY + 15) + 'px';
        });

        // === 14.5. ГЛИТЧ-ЭФФЕКТ НА ЗАГОЛОВКАХ ===
        setInterval(() => {
            if (Math.random() < 0.4) {
                const headings = document.querySelectorAll('h1, h2, .card-title');
                if (!headings.length) return;
                const h = pick(Array.from(headings));
                h.classList.add('coder-glitch-text');
                setTimeout(() => h.classList.remove('coder-glitch-text'), 300);
            }
        }, 5000);

        // === 14.6. СЛУЧАЙНЫЙ SVG-ШУМ ===
        setInterval(() => {
            if (Math.random() < 0.2) {
                spawnSVG(SVG.noise, {
                    x: rand(0, window.innerWidth - 300),
                    y: rand(0, window.innerHeight - 200),
                    size: randInt(200, 400),
                    className: 'svg-effect--pop',
                    duration: 1.2,
                });
            }
        }, 8000);
    }

    // ============================================
    // 15. РОЛЬ: ADMIN — ЗОЛОТЫЕ ИСКРЫ
    // ============================================

    if (isAdmin) {
        document.body.classList.add('admin-mode');

        setInterval(() => {
            if (Math.random() < 0.6) {
                spawnGoldSpark();
            }
        }, 1500);

        setInterval(() => {
            if (Math.random() < 0.4) {
                const cards = document.querySelectorAll('.card, .stat-card');
                if (!cards.length) return;
                const card = pick(Array.from(cards));
                spawnGoldSparkAt(card);
            }
        }, 3000);

        const crown = document.querySelector('.admin-crown');
        if (crown) {
            setInterval(() => {
                crown.style.transform = `scale(1.05) rotate(${rand(-2, 2)}deg)`;
                setTimeout(() => {
                    crown.style.transform = '';
                }, 300);
            }, 4000);
        }
    }

    function spawnGoldSpark() {
        const spark = document.createElement('div');
        spark.className = 'gold-spark';
        spark.style.left = rand(0, 100) + 'vw';
        spark.style.top = rand(0, 100) + 'vh';
        spark.style.width = spark.style.height = randInt(3, 7) + 'px';
        spark.style.animationDuration = rand(1.5, 3) + 's';
        spark.style.pointerEvents = 'none';
        document.body.appendChild(spark);

        setTimeout(() => spark.remove(), 3500);
    }

    function spawnGoldSparkAt(parent) {
        const rect = parent.getBoundingClientRect();
        for (let i = 0; i < 3; i++) {
            const spark = document.createElement('div');
            spark.className = 'gold-spark';
            spark.style.left = (rect.left + rand(0, rect.width)) + 'px';
            spark.style.top = (rect.top + rand(0, rect.height)) + 'px';
            spark.style.position = 'fixed';
            spark.style.width = spark.style.height = randInt(2, 5) + 'px';
            spark.style.animationDuration = rand(1.2, 2.5) + 's';
            spark.style.pointerEvents = 'none';
            document.body.appendChild(spark);

            setTimeout(() => spark.remove(), 3000);
        }
    }

    // ============================================
    // 16. РОЛЬ: GHOST — МЕРЦАНИЕ АВАТАРКИ
    // ============================================

    if (page.querySelector('.avatar-role-ghost')) {
        document.body.classList.add('ghost-mode');

        setInterval(() => {
            if (Math.random() < 0.2) {
                document.body.style.opacity = '0.96';
                setTimeout(() => {
                    document.body.style.opacity = '';
                }, 100);
            }
        }, 6000);

        const avatarWrap = document.querySelector('.profile-avatar-wrap');
        if (avatarWrap) {
            setInterval(() => {
                spawnGhostParticle(avatarWrap);
            }, 800);
        }
    }

    function spawnGhostParticle(parent) {
        const rect = parent.getBoundingClientRect();
        const particle = document.createElement('div');
        particle.className = 'ghost-particle';
        particle.style.position = 'fixed';
        particle.style.left = (rect.left + rand(0, rect.width)) + 'px';
        particle.style.top = (rect.top + rand(0, rect.height)) + 'px';
        particle.style.width = particle.style.height = randInt(3, 6) + 'px';
        particle.style.animationDuration = rand(2, 4) + 's';
        particle.style.pointerEvents = 'none';
        document.body.appendChild(particle);

        setTimeout(() => particle.remove(), 4500);
    }

})();