
const canvas = document.getElementById('output-canvas');
const ctx = canvas.getContext('2d');
const video = document.getElementById('input-video');

// Screens
const screens = {
    start: document.getElementById('start-screen'),
    settings: document.getElementById('settings-screen'),
    storyConfig: document.getElementById('story-config-screen'),
    hud: document.getElementById('hud'),
    gameOver: document.getElementById('game-over-screen'),
    stageClear: document.getElementById('stage-clear-screen')
};

// UI Elements
const els = {
    score: document.getElementById('score'),
    time: document.getElementById('time'),
    modeDisplay: document.getElementById('mode-display'),
    settingsList: document.getElementById('settings-list'),
    storySettingsList: document.getElementById('story-settings-list'),
    stageSelector: document.getElementById('stage-display'),
    stageInfo: document.getElementById('stage-info'),
    targetInfo: document.getElementById('target-info'),
    finalScore: document.getElementById('final-score'),
    goStoryInfo: document.getElementById('go-story-info')
};

// Assets
const assets = {
    banana: new Image(),
    orange: new Image(),
    music: new Audio('assets/techno.mp3')
};
assets.banana.src = 'assets/icon/banana.png';
assets.orange.src = 'assets/icon/orange.png';
assets.music.loop = true;

// Game Constants
const MODES = { FREE: 'FREE', STORY: 'STORY' };

// Helpers
function randRange(min, max) { return Math.random() * (max - min) + min; }
function randInt(min, max) { return Math.floor(randRange(min, max)); }

class Fruit {
    constructor(w, h, speedMult, direction) {
        this.type = Math.random() < 0.5 ? 'banana' : 'orange';
        this.radius = 30;
        this.w = w;
        this.h = h;
        this.direction = direction;

        const baseSpeed = randRange(5, 10);
        this.speed = baseSpeed * speedMult;

        if (direction === 'Up') {
            this.x = randInt(50, w - 50);
            this.y = h + 50;
        } else if (direction === 'Diagonal') {
            this.x = randInt(50, w - 50);
            this.y = -50;
            this.dx = (Math.random() < 0.5 ? -1 : 1) * (this.speed * 0.5);
        } else { // Down
            this.x = randInt(50, w - 50);
            this.y = -50;
        }
    }

    update() {
        if (this.direction === 'Up') {
            this.y -= this.speed;
        } else if (this.direction === 'Diagonal') {
            this.y += this.speed;
            this.x += this.dx;
            if (this.x < 0 || this.x > this.w) this.dx *= -1;
        } else {
            this.y += this.speed;
        }
    }

    draw(ctx) {
        const img = this.type === 'banana' ? assets.banana : assets.orange;
        if (img.complete && img.naturalHeight !== 0) {
            const size = 60;
            ctx.drawImage(img, this.x - size / 2, this.y - size / 2, size, size);
        } else {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
            ctx.fillStyle = this.type === 'banana' ? 'yellow' : 'orange';
            ctx.fill();
            ctx.strokeStyle = 'white';
            ctx.lineWidth = 2;
            ctx.stroke();
        }
    }
}

class Game {
    constructor() {
        this.state = 'START';
        this.mode = MODES.FREE;

        this.freeSettings = {
            duration: { options: [30, 60, 90, 120], idx: 1, label: 'Game Duration (s)' },
            spawn_rate: { options: [1.5, 1.0, 0.5, 0.3], idx: 1, label: 'Spawn Rate (s)' },
            speed_mult: { options: [0.5, 1.0, 1.5, 2.0], idx: 1, label: 'Fall Speed' },
            direction: { options: ['Down', 'Diagonal', 'Up'], idx: 0, label: 'Direction' }
        };

        this.storyConfig = [
            { duration: 30, spawn_rate: 1.5, speed_mult: 0.5, direction: 'Down' },
            { duration: 45, spawn_rate: 1.0, speed_mult: 1.0, direction: 'Down' },
            { duration: 60, spawn_rate: 1.0, speed_mult: 1.5, direction: 'Diagonal' },
            { duration: 60, spawn_rate: 0.5, speed_mult: 1.5, direction: 'Diagonal' },
            { duration: 90, spawn_rate: 0.3, speed_mult: 2.0, direction: 'Up' }
        ];
        this.storyOptions = {
            duration: [30, 45, 60, 90, 120],
            spawn_rate: [2.0, 1.5, 1.0, 0.5, 0.3],
            speed_mult: [0.5, 1.0, 1.5, 2.0, 3.0],
            direction: ['Down', 'Diagonal', 'Up']
        };

        this.currentStage = 0;
        this.score = 0;
        this.startTime = 0;
        this.fruits = [];
        this.effects = [];
        this.lastSpawnTime = 0;
        this.retryCount = 0;

        this.inputHandling();
        this.updateUI();
    }

    inputHandling() {
        window.addEventListener('keydown', (e) => {
            const key = e.key.toLowerCase();
            let valid = false;
            let expected = [];

            // Global Keys
            if (['q', 'escape'].includes(key)) valid = true;

            // State-specific validation
            if (this.state === 'START') {
                expected = ['s', 'p', 'm', 'q', 'escape'];
                if (expected.includes(key)) valid = true;
            } else if (this.state === 'SETTINGS') {
                expected = ['1', '2', '3', '4', 'b', 'p', 'q', 'escape'];
                if (expected.includes(key)) valid = true;
            } else if (this.state === 'STORY_CONFIG') {
                expected = ['1', '2', '3', '4', 'b', 'p', ',', '.', '<', '>', 'q', 'escape'];
                if (expected.includes(key)) valid = true;
            } else if (this.state === 'GAMEOVER') {
                expected = ['r', 'p', 'q', 'escape'];
                if (expected.includes(key)) valid = true;
            } else if (this.state === 'PLAYING') {
                // In playing, most keys are ignored or valid?
                // If we want to detect "pressing S during playing" -> erroneous.
                // Let's say only global keys are valid UI inputs.
                expected = ['q', 'escape'];
                if (expected.includes(key)) valid = true;
            } else {
                // Other states (STAGE_CLEAR etc) -> maybe ignore or block
                valid = false;
            }

            if (!valid && this.state !== 'PLAYING') {
                // Log Erroneous (Skip playing because they might be mash/motion noise, unless strictly undesired)
                // User requirement: "misoperation... different from instructions".
                // In playing, there are no instructions to press keys (except Q).
                // So hitting 'S' is definitely erroneous.
                if (window.sendLog) window.sendLog({
                    type: 'erroneous_input',
                    key: key,
                    state: this.state,
                    expected: expected,
                    description: "User pressed unexpected key."
                });
                return;
            }

            // If we are playing and key is invalid, we might still want to log it?
            // "misoperation". Hitting spacebar during game = misoperation?
            // Let's log it for PLAYING too if distinct enough. 
            // The check `!valid && this.state !== 'PLAYING'` skipped it.
            // Let's remove that exclusion to catch all.
            if (!valid) {
                if (window.sendLog) window.sendLog({
                    type: 'erroneous_input',
                    key: key,
                    state: this.state,
                    expected: expected,
                    description: "User pressed unexpected key."
                });
                return;
            }

            // Normal Logic
            if (window.sendKeyLog) window.sendKeyLog(key); // Standard tracking for valid keys

            if (key === 'q' || key === 'escape') {
                if (this.state === 'PLAYING') {
                    this.state = 'START';
                    this.stopMusic();
                }
            }

            if (this.state === 'START') {
                if (key === 's') this.startGame();
                if (key === 'p') this.state = this.mode === MODES.FREE ? 'SETTINGS' : 'STORY_CONFIG';
                if (key === 'm') {
                    this.mode = this.mode === MODES.FREE ? MODES.STORY : MODES.FREE;
                    document.body.className = this.mode === MODES.STORY ? 'mode-story' : '';
                }
            } else if (this.state === 'SETTINGS') {
                if (key === 'b' || key === 'p') this.state = 'START';
                if (['1', '2', '3', '4'].includes(key)) {
                    const keys = Object.keys(this.freeSettings);
                    const idx = parseInt(key) - 1;
                    if (idx < keys.length) {
                        const k = keys[idx];
                        const s = this.freeSettings[k];
                        s.idx = (s.idx + 1) % s.options.length;
                    }
                }
            } else if (this.state === 'STORY_CONFIG') {
                if (key === 'b' || key === 'p') this.state = 'START';
                if (key === ',' || key === '<') this.currentStage = Math.max(0, this.currentStage - 1);
                if (key === '.' || key === '>') this.currentStage = Math.min(4, this.currentStage + 1);

                const cfg = this.storyConfig[this.currentStage];
                const opt = this.storyOptions;
                if (key === '1') cfg.duration = this.nextOpt(opt.duration, cfg.duration);
                if (key === '2') cfg.spawn_rate = this.nextOpt(opt.spawn_rate, cfg.spawn_rate);
                if (key === '3') cfg.speed_mult = this.nextOpt(opt.speed_mult, cfg.speed_mult);
                if (key === '4') cfg.direction = this.nextOpt(opt.direction, cfg.direction);

            } else if (this.state === 'GAMEOVER') {
                if (key === 'r') this.state === 'GAMEOVER' && this.restartGame(); // Check state to prevent rapid R
                if (key === 'p') this.state = this.mode === MODES.FREE ? 'SETTINGS' : 'STORY_CONFIG';
            }

            this.updateUI();
        });
    }

    nextOpt(arr, current) {
        const i = arr.indexOf(current);
        return arr[(i + 1) % arr.length];
    }

    startGame(restartStage = false) {
        this.score = 0;
        this.startTime = Date.now();
        this.fruits = [];
        this.effects = [];
        this.lastSpawnTime = 0;

        if (this.mode === MODES.STORY && !restartStage) {
            // If new game, start at 0. If just restarting stage, keep currentStage.
            // But from START screen 'S' means new game usually.
            // Let's assume 'S' from START resets to Stage 1. 
            // We need a way to know if we are restarting a stage or starting fresh.
            // The method argument handles it.
            if (this.state === 'START') {
                this.currentStage = 0;
                this.retryCount = 0;
            }
        } else {
            // Free Mode: reset retry on start
            if (this.state === 'START') this.retryCount = 0;
        }

        // Apply Settings
        if (this.mode === MODES.FREE) {
            const s = this.freeSettings;
            this.gameDuration = s.duration.options[s.duration.idx];
            this.spawnRate = s.spawn_rate.options[s.spawn_rate.idx];
            this.speedMult = s.speed_mult.options[s.speed_mult.idx];
            this.direction = s.direction.options[s.direction.idx];
            this.targetScore = 0;
        } else {
            const cfg = this.storyConfig[this.currentStage];
            this.gameDuration = cfg.duration;
            this.spawnRate = cfg.spawn_rate;
            this.speedMult = cfg.speed_mult;
            this.direction = cfg.direction;

            const totalDrops = this.gameDuration / this.spawnRate;
            this.targetScore = Math.floor(totalDrops * 3 * 0.60);
        }

        this.state = 'PLAYING';
        this.playMusic();
        this.updateUI();
    }

    restartGame() {
        // If Story Mode and we cleared (won whole story), reset to stage 0?
        // Logic: Retry current stage.
        // If all stages cleared, maybe reset to 0.
        // But user said "R restarts".
        if (this.mode === MODES.STORY && this.score >= this.targetScore && this.currentStage === 4) {
            this.currentStage = 0;
            this.retryCount = 0; // Reset if restarting whole story
        } else {
            this.retryCount++;
        }
        this.startGame(true);
    }

    playMusic() {
        assets.music.currentTime = 0;
        assets.music.play().catch(e => console.log("Audio play failed (maybe need interaction):", e));
    }

    stopMusic() {
        assets.music.pause();
    }

    updateUI() {
        // Hide all
        Object.values(screens).forEach(s => s.classList.add('hidden'));

        if (this.state === 'START') {
            screens.start.classList.remove('hidden');
            els.modeDisplay.textContent = `MODE: ${this.mode}`;
        } else if (this.state === 'SETTINGS') {
            screens.settings.classList.remove('hidden');
            // Render list
            let html = '';
            Object.keys(this.freeSettings).forEach((k, i) => {
                const item = this.freeSettings[k];
                html += `<div class="setting-item">${i + 1}. ${item.label}: ${item.options[item.idx]}</div>`;
            });
            els.settingsList.innerHTML = html;
        } else if (this.state === 'STORY_CONFIG') {
            screens.storyConfig.classList.remove('hidden');
            els.stageSelector.textContent = `< Stage ${this.currentStage + 1} >`;
            const cfg = this.storyConfig[this.currentStage];
            let html = `
                <div class="setting-item">1. Duration: ${cfg.duration}s</div>
                <div class="setting-item">2. Spawn Rate: ${cfg.spawn_rate}s</div>
                <div class="setting-item">3. Speed Mult: ${cfg.speed_mult}x</div>
                <div class="setting-item">4. Direction: ${cfg.direction}</div>
            `;
            els.storySettingsList.innerHTML = html;
        } else if (this.state === 'PLAYING') {
            screens.hud.classList.remove('hidden');
            if (this.mode === MODES.STORY) {
                els.stageInfo.classList.remove('hidden');
                els.stageInfo.textContent = `Stage: ${this.currentStage + 1}/5`;
                els.targetInfo.classList.remove('hidden');
                els.targetInfo.textContent = `Target: ${this.targetScore}`;
            } else {
                els.stageInfo.classList.add('hidden');
                els.targetInfo.classList.add('hidden');
            }
        } else if (this.state === 'GAMEOVER') {
            screens.gameOver.classList.remove('hidden');
            els.finalScore.textContent = `Final Score: ${this.score}`;

            if (this.mode === MODES.STORY) {
                els.goStoryInfo.classList.remove('hidden');
                if (this.score >= this.targetScore && this.currentStage === 4) {
                    screens.gameOver.querySelector('h1').textContent = "ALL STAGES CLEARED!";
                    screens.gameOver.querySelector('h1').style.color = "#0f0";
                    els.goStoryInfo.textContent = "";
                } else if (this.score < this.targetScore) {
                    screens.gameOver.querySelector('h1').textContent = "STAGE FAILED...";
                    screens.gameOver.querySelector('h1').style.color = "#f00";
                    els.goStoryInfo.textContent = `Target was: ${this.targetScore}`;
                }
            } else {
                screens.gameOver.querySelector('h1').textContent = "GAME OVER";
                screens.gameOver.querySelector('h1').style.color = "#f00";
                els.goStoryInfo.classList.add('hidden');
            }
        } else if (this.state === 'STAGE_CLEAR') {
            screens.stageClear.classList.remove('hidden');
            screens.stageClear.querySelector('h1').textContent = `STAGE ${this.currentStage} CLEARED!`;
        }
    }

    update(landmarks) {
        if (this.state !== 'PLAYING') return;

        const now = Date.now();
        const elapsed = (now - this.startTime) / 1000;
        const remaining = Math.max(0, this.gameDuration - elapsed);

        els.time.textContent = `Time: ${Math.floor(remaining)}`;
        els.score.textContent = `Score: ${this.score}`;
        els.time.classList.toggle('low-time', remaining <= 10);

        if (remaining <= 0) {
            this.checkGameOver();
            return;
        }

        // Spawn
        if (now - this.lastSpawnTime > this.spawnRate * 1000) {
            this.fruits.push(new Fruit(canvas.width, canvas.height, this.speedMult, this.direction));
            this.lastSpawnTime = now;
        }

        // Collision & Logic
        // Interaction points: Nose(0), Wrists(15,16), Foot Indices(31,32)
        const relevantLandmarks = [
            { idx: 0, pts: 3 }, // Head
            { idx: 15, pts: 1 }, // L Wrist
            { idx: 16, pts: 1 }, // R Wrist
            { idx: 31, pts: 2 }, // L Foot
            { idx: 32, pts: 2 }  // R Foot
        ];

        for (let i = this.fruits.length - 1; i >= 0; i--) {
            let f = this.fruits[i];
            f.update();

            let caught = false;
            // Collision detection
            if (landmarks) {
                for (let lm of relevantLandmarks) {
                    const p = landmarks[lm.idx];
                    if (p && p.visibility > 0.5) {
                        const px = p.x * canvas.width;
                        const py = p.y * canvas.height;
                        const dist = Math.hypot(px - f.x, py - f.y);

                        if (dist < 50 + f.radius) {
                            caught = true;
                            this.score += lm.pts;
                            this.effects.push({ Rx: f.x, Ry: f.y, r: 10 });
                            break;
                        }
                    }
                }
            }

            let remove = caught;
            if (f.direction === 'Up' && f.y < -50) remove = true;
            if (f.direction !== 'Up' && f.y > canvas.height + 50) remove = true;

            if (remove) {
                this.fruits.splice(i, 1);
            }
        }
    }

    draw(ctx, landmarks) {
        // Effects
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 3;
        for (let i = this.effects.length - 1; i >= 0; i--) {
            let e = this.effects[i];
            e.r += 5;
            ctx.beginPath();
            ctx.arc(e.Rx, e.Ry, e.r, 0, Math.PI * 2);
            ctx.stroke();
            if (e.r > 50) this.effects.splice(i, 1);
        }

        // Fruits
        this.fruits.forEach(f => f.draw(ctx));

        // Landmarks (Simplified drawing)
        if (landmarks && this.state === 'PLAYING') {
            const h = canvas.height;
            const w = canvas.width;

            // Draw points
            const pts = [
                { idx: 0, c: 'blue' },
                { idx: 15, c: 'lime' }, { idx: 16, c: 'lime' },
                { idx: 31, c: 'red' }, { idx: 32, c: 'red' }
            ];

            pts.forEach(p => {
                const lm = landmarks[p.idx];
                if (lm && lm.visibility > 0.5) {
                    ctx.beginPath();
                    ctx.arc(lm.x * w, lm.y * h, 15, 0, Math.PI * 2);
                    ctx.fillStyle = p.c;
                    ctx.fill();
                }
            });
        }
    }

    checkGameOver() {
        this.stopMusic();
        if (this.mode === MODES.FREE) {
            this.state = 'GAMEOVER';
            this.updateUI();

            // Log Game Over (Free)
            if (window.sendLog) window.sendLog({
                type: 'game_over',
                mode: 'FREE',
                score: this.score,
                duration: this.gameDuration,
                retryCount: this.retryCount
            });

        } else {
            if (this.score >= this.targetScore) {
                if (this.currentStage < 4) {

                    // Log Stage Clear
                    if (window.sendLog) window.sendLog({
                        type: 'stage_clear',
                        mode: 'STORY',
                        stage: this.currentStage + 1,
                        score: this.score,
                        target: this.targetScore,
                        retryCount: this.retryCount
                    });
                    // Reset retry count for next stage? User request: "where stage repeated". So cumulative or per stage?
                    // Usually retry count is interesting per stage. Let's keep it cumulative for the session or reset?
                    // Let's NOT reset here to track total retries, OR reset to track per-stage difficulty.
                    // User said "how many times repeated *where*". Implies per stage tracking.
                    this.retryCount = 0;

                    this.currentStage++;
                    this.state = 'STAGE_CLEAR';
                    this.updateUI();
                    setTimeout(() => {
                        if (this.state === 'STAGE_CLEAR') this.startGame(true);
                    }, 3000);
                } else {
                    this.state = 'GAMEOVER';
                    this.updateUI();

                    // Log All Cleared
                    if (window.sendLog) window.sendLog({
                        type: 'game_over',
                        mode: 'STORY',
                        result: 'ALL_CLEARED',
                        score: this.score,
                        finalStage: this.currentStage + 1,
                        retryCount: this.retryCount
                    });
                }
            } else {
                this.state = 'GAMEOVER';
                this.updateUI();

                // Log Fail
                if (window.sendLog) window.sendLog({
                    type: 'game_over',
                    mode: 'STORY',
                    result: 'FAILED',
                    stage: this.currentStage + 1,
                    score: this.score,
                    target: this.targetScore,
                    retryCount: this.retryCount
                });
            }
        }
    }
}

const game = new Game();

// MediaPipe Setup
const pose = new Pose({
    locateFile: (file) => {
        return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
    }
});
pose.setOptions({
    modelComplexity: 1,
    smoothLandmarks: true,
    enableSegmentation: false,
    smoothSegmentation: false,
    minDetectionConfidence: 0.5,
    minTrackingConfidence: 0.5
});

pose.onResults(onResults);

const camera = new Camera(video, {
    onFrame: async () => {
        await pose.send({ image: video });
    },
    width: 1280,
    height: 720
});
camera.start();

function onResults(results) {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Draw Video Frame
    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(results.image, 0, 0, canvas.width, canvas.height);

    // Draw Skeleton
    if (results.poseLandmarks) {
        drawConnectors(ctx, results.poseLandmarks, POSE_CONNECTIONS,
            { color: '#00FF00', lineWidth: 4 });
    }

    // Game Update & Draw (Overlays)
    game.update(results.poseLandmarks);
    game.draw(ctx, results.poseLandmarks);

    ctx.restore();
}
